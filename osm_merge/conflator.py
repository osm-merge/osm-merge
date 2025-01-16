#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024, 2025 OpenStreetMap US
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
import argparse
import logging
import sys
import os
import re
from sys import argv
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, MultiLineString, Polygon, mapping
import shapely
from shapely.ops import transform, nearest_points, linemerge
from shapely import wkt
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
# from osm_fieldwork.convert import escape
# from osm_fieldwork.parsers import ODKParsers
import pyproj
import asyncio
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from haversine import haversine, Unit
from thefuzz import fuzz, process
from pathlib import Path
from osm_merge.fieldwork.parsers import ODKParsers
from osm_merge.osmfile import OsmFile
from pathlib import Path
# from spellchecker import SpellChecker
# from osm_rawdata.pgasync import PostgresClient
from tqdm import tqdm
import tqdm.asyncio
import xmltodict
from numpy import arccos, array
from numpy.linalg import norm
import math
import numpy

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
# Try doubling the number of cores, since the CPU load is
# still reasonable.
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# Shapely.distance doesn't like duplicate points
warnings.simplefilter(action='ignore', category=RuntimeWarning)

# # A function that returns the 'year' value:
# def distSort(data: list):
#     """
#     Args:
#         data (list): The data to sort
#     """
#     return data['dist']

# def hitsSort(data: list):
#     """
#     Args:
#         data (list): The data to sort
#     """
#     return data['hits']

# def angleSort(data: list):
#     """
#     Args:
#         data (list): The data to sort
#     """
#     return data['angle']

def conflateThread(primary: list,
                   secondary: list,
                   informal: bool = False,
                   threshold: float = 7.0,
                   spellcheck: bool = True,
                   ) -> list:
    """
    Conflate features from ODK against all the features in OSM.

    Args:
        primary (list): The external dataset to conflate
        seconday (list): The secondzry dataset, probably existing OSM data
        threshold (int): Threshold for distance calculations
        informal (bool): Whether to dump features in OSM not in external data
        spellcheck (bool): Whether to also spell check string values

    Returns:
        (list):  The conflated output
    """
    # log.debug(f"Dispatching thread ")

    #timer = Timer(text="conflateFeatures() took {seconds:.0f}s")

    # ODK data is always a single node when mapping buildings, but the
    # OSM data will be a mix of nodes and ways. For the OSM data, the
    # building centroid is used.

    # Most smartphone GPS are 5-10m off most of the time, plus sometimes
    # we're standing in front of an amenity and recording that location
    # instead of in the building.
    # gps_accuracy = 10
    # this is the treshold for fuzzy string matching
    match_threshold = 80
    data = list()
    newdata = list()
    # New features not in OSM always use negative IDs
    odkid = -100
    osmid = 0
    nodes = dict()
    version = 0

    cutils = Conflator()
    i = 0

    log.info(f"The primary dataset has {len(primary)} entries")
    log.info(f"The secondary dataset has {len(secondary)} entries")
    
    # Progress bar
    pbar = tqdm.tqdm(primary)
    for entry in pbar:
        # for entry in primary:
        i += 1
        # timer.start()
        confidence = 0
        maybe = list()
        # If an OSM file is the primary, ignore the nodes that comprise the
        # LineString.
        # log.debug(f"ENTRY: {entry["properties"]}")
        if entry["geometry"]["type"] == "Point":
            continue

        print(f"PRIMARY: {entry["properties"]}")
        for existing in secondary:
            # FIXME: debug
            if existing["geometry"]["type"] == "Point":
                continue
            foo = f"ID: {existing["properties"]["id"]}, "
            if "name" in existing["properties"]:
                foo += f"NAME: {existing["properties"]["name"]}, "
            if "highway" in existing["properties"]:
                foo += f"HIGHWAY: {existing["properties"]["highway"]}, "
            if "ref" in existing["properties"]:
                foo += f"REF: {existing["properties"]["ref"]}, "
            if "ref:usfs" in existing["properties"]:
                foo += f"REF:USFS: {existing["properties"]["ref:usfs"]}, "
            if len(foo) < 0:
                print(f"\tSECONDARY: {foo}")
            feature = dict()
            newtags = dict()
            # log.debug(f"EXISTING: {existing["properties"]}")
            if existing["geometry"] is not None:
                if existing["geometry"]["type"] == "Point":
                    # data.append(existing)
                    continue
            geom = None
            # We could probably do this using GeoPandas or gdal, but that's
            # going to do the same brute force thing anyway.

            # If the input file is in OSM XML format, we don't want to
            # conflate the nodes with no tags. They are used to build
            # the geometry for the way, and after that aren't needed anymore.
            # If the node has tags, then it's a POI, which we do conflate.
            # log.debug(entry)
            if entry["geometry"] is None or existing["geometry"] is None:
                # Obviously can't do a distance comparison is a geometry is missing
                continue
            if entry["geometry"]["type"] == "Point": #  and len(entry["properties"]) <= 2:
                continue
            if existing["geometry"]["type"] == "Point": # and len(existing["properties"]) <= 2:
                continue
            # FIXME: some LineStrings are only two points, there two refs,
            # but only one set of coordinates.
            if existing["geometry"]["type"] == "LineString" and len(existing["geometry"]["coordinates"]) <= 1:
                continue

            dist = float()
            slope = float()
            hits = 0
            angle_threshold = 17.0 # 20.0 # the angle between two lines
            slope_threshold = 4.0 # the slope between two lines
            match_threshold = 80 # the ratio for name and ref matching
            name1 = None
            name2 = None
            match = False
            try:
                dist = cutils.getDistance(entry, existing)
            except:
                log.error(f"getDistance() just had a weird error")
                log.error(f"ENTRY: {entry}")
                log.error(f"EXISTING: {existing}")
                breakpoint()
                continue

            # This is only returned when the difference in linestring
            # length is large, which often means the OSM highway doesn't
            # exist in the external dataset.
            if dist < 0:
                continue
            # log.debug(f"ENTRY: {dist}: {entry["properties"]}")
            # log.debug(f"EXISTING: {existing["properties"]}")
            if abs(dist) >= threshold:
                continue
            else:
                print("------------------------------------------------------")
                if "id" not in existing["properties"]:
                    existing["properties"]["id"] = -1
                angle = 0.0
                try:
                    slope, angle = cutils.getSlope(entry, existing)
                except:
                    log.error(f"getSlope() just had a weird error")
                    print(f"\tENTRY: {entry["properties"]}")
                    print(f"\tEXISTING: {existing["properties"]}")
                    # breakpoint()
                    # slope, angle = cutils.getSlope(entry, existing)
                    continue
                if abs(angle) > angle_threshold or abs(slope) > slope_threshold:
                    print(f"\tOut of range: {slope} : {angle}")
                    # print(f"PRIMARY: {entry["properties"]}")
                    # print(f"SECONDARY: {existing["properties"]}")
                    continue
                # log.debug(f"DIST: {dist}, ANGLE: {angle}, SLOPE: {slope}")
                # log.debug(f"PRIMARY: {entry["properties"]}")
                # log.debug(f"SECONDARY: {existing["properties"]}")
                hits, tags = cutils.checkTags(entry, existing)
                tags["debug"] = f"hits: {hits}, dist: {str(dist)[:7]}, slope: {str(slope)[:7]}, angle: {str(angle)[:7]}"
                if "name" in existing["properties"]:
                    name2 = existing["properties"]["name"]
                if "name" in entry["properties"]:
                    name1 = entry["properties"]["name"]
                if (abs(angle) > angle_threshold or abs(slope) > slope_threshold):
                    continue
                print(f"HITS: {hits}, DIST: {str(dist)[:7]}, NAME: {tags["name_ratio"]}, REF: {tags["ref_ratio"]}, SLOPE: {slope:.3f}, Angle: {angle:.3f},  - {name1} == {name2}")
                foo = tags
                if "ref" in foo:
                    del foo["ref"]
                print(f"\tTAGs: {foo}")
                # breakpoint()
                # Don't add highways that match
                match = False
                if hits == 3: # or (slope == 0.0 and angle == 0.0):
                    # (tags["name_ratio"] >= match_threshold or tags["ref_ratio"] >= match_threshold)
                    if entry['properties'] != existing['properties']:
                        # if tags["name_ratio"] >= match_threshold or tags["ref_ratio"] <= match_threshold:
                        #     log.debug(f"\tName or ref didn't match!")
                        # else:
                        # Only add the feature to the output if there are
                        # differences in the tags. If they are identical,
                        # ignore it as no changes need to be made.
                        print(f"\tAlmost Perfect match, name and ref!")
                    else:
                        log.debug(f"\tPerfect match! {entry['properties']}")
                    # print(f"\tENTRY1: {entry["properties"]}")
                    # print(f"\tEXISTING1: {existing["properties"]}")
                    maybe = list()
                    hits = 0
                    break
                elif hits == 2 and dist == 0.0:
                    log.debug(f"\tName and ref matched, geom close")
                    # print(f"\tENTRY1: {entry["properties"]}")
                    # print(f"\tEXISTING1: {existing["properties"]}")
                    hits = 0
                    maybe = list()
                    break
                elif hits == 1 and dist <= 2.0:
                    if tags["name_ratio"] == 0 and tags["ref_ratio"] >= match_threshold:
                        log.debug(f"Ref matched, no name in data, geom close")
                        # breakpoint()
                        if "name" not in tags:
                            break
                    elif (tags["name_ratio"] >= match_threshold and tags["ref_ratio"] == 0):
                        log.debug(f"Name matched, no ref in data, geom close")
                        if "ref:usfs" not in tags:
                            break
                elif hits == 0 and dist == 0.0:
                    log.debug(f"\tGeometry was close, OSM was probably lacking the name")
                    # print(f"\tENTRY2: {entry["properties"]}")
                    # print(f"\tEXISTING2: {existing["properties"]}")
                    if "name" in entry["properties"] or "ref:usfs" in entry["properties"]:
                        hits += 1
                elif hits == 2 and dist == 0.0:
                    log.debug(f"\tName and ref matched, geom close")
                    # print(f"\tENTRY4: {entry["properties"]}")
                    # print(f"\tEXISTING4: {existing["properties"]}")
                    maybe = list()
                    hits = 0
                    break
                elif hits == 1 and tags["name_ratio"] >= match_threshold:
                    if tags["name_ratio"] == 0 and tags["ref_ratio"] > 80:
                        log.debug(f"\tClose geometry match, ref match")
                        if not "name" in tags:
                            break
                    elif tags["name_ratio"] > 0 and tags["ref_ratio"] == 0:
                        log.debug(f"\tClose geometry match, name match, not ref")
                        if not "name" in tags:
                            break
                    else:
                        log.error(f"Name and ref don't match!")
                    # print(f"\tENTRY5: {entry["properties"]}")
                    # print(f"\tEXISTING5: {existing["properties"]}")
                    hits += 1
                elif hits == 2:
                    if tags["name_ratio"] == match_threshold and tags["ref_ratio"] >= match_threshold:
                        log.debug(f"\tName matched and ref matched")
                        # print(f"\tENTRY6: {entry["properties"]}")
                        # print(f"\tEXISTING6: {existing["properties"]}")
                    hits += 1
                    break
                elif hits == 0 and dist == 0.0:
                    log.debug(f"\tGeometry matched, no name or ref in OSM")
                    print(f"\tENTRY7: {entry["properties"]}")
                    print(f"\tEXISTING7: {existing["properties"]}")
                    hits += 1
                elif angle == 0.0 and slope == 0.0 and dist == 0.0:
                    log.debug(f"\tGeometry matched, not name")
                    # print(f"\tENTRY8: {entry["properties"]}")
                    # print(f"\tEXISTING8: {existing["properties"]}")
                    hits += 1

                if hits > 0:
                    maybe.append({"hits": hits, "dist": dist, "angle": angle, "slope": slope, "name_ratio": tags["name_ratio"], "match": match, "ref_ratio": tags["ref_ratio"], "osm": existing})
                    # data.append(Feature(geometry=geom, properties=tags))

                # cache all OSM features within our threshold distance
                # These are needed by ODK, but duplicates of other fields,
                # so they aren't needed and just add more clutter.
                # log.debug(f"DIST: {dist / 1000}km. {dist}m")
                # maybe.append({"hits": hits, "dist": dist, "slope": slope, "angle": angle, "hits": hits, "odk": entry, "osm": existing})
                # don't keep checking every highway, although testing seems
                # to show 99% only have one distance match within range.
                if len(maybe) >= 7:
                    # FIXME: it turns out sometimes the other nearby highways are
                    # segments of the same highway, but the tags only get added
                    # to the closest segment.
                    log.debug(f"Have enough matches.")
                    break

        # log.debug(f"MAYBE: {len(maybe)}")
        if len(maybe) > 0 :
            # cache the refs to use in the OSM XML output file
            refs = list()
            # odk = dict()
            # osm = dict()
            slope = float()
            angle = float()
            dist = float()
            # There are two parameters used to decide on the probably
            # match. If we have at least 2 hits, it's very likely a
            # good match, 3 is a perfect match.
            best = None
            # maybe.sort(key=hitsSort)
            # maybe.sort(key=distSort)

            # Sometimes all the maybes are segments of the same highway.
            # maybe.sort(key=distSort)
            # maybe.sort(key=angleSort)
            # maybe.sort(key=hitsSort)
            best = 0
            ratio = 0
            closest = None
            hits = 0
            # if len(maybe) > 1:
            #     breakpoint()
            for segment in maybe:
                # FIXME: this is a test to see if adding the ratios, along with
                # distance can find the best match in the maype list.
                ratio =  segment["name_ratio"] + segment["ref_ratio"]
                # print(f"RATIO: {ratio} - {segment["match"]}")
                # It was a solid match, so doesn't go in any output files
                if segment["match"]:
                    continue
                # Ref or name matched, geometry close
                # elif segment["hits"] == 2 and ratio >= 100:
                #     print(f"Good match!")
                #     break
                # elif segment["hits"] == 1:
                #     print(f"Poor match!")
                #     # breakpoint()
                #     break
                # elif segment["hits"] == 0:
                #     print(f"No match!")
                #     # breakpoint()
                #     break
                # if ratio >= best:
                #     closest = segment
                if segment["hits"] > hits:
                    hits = segment["hits"]
                    closest = segment
                props = closest["osm"]["properties"]
                tags = entry["properties"]
                if "refs" in props:
                    tags["refs"] = props["refs"]
                if "osm_id" in props:
                    tags["id"] = props["osm_id"]
                elif "id" in props:
                    tags["id"] =  props["id"]
                if "version" in props:
                    tags["version"] = props["version"]
                else:
                    tags["version"] = 1
                if "name_ration" in segment:
                    tags["name_ratio"] = segment["name_ratio"]
                if "ref_ration" in segment:
                    tags["ref_ratio"] = segment["ref_ratio"]

                tags["debug"] = f"hits: {hits}, dist: {str(closest["dist"])[:7]}, slope: {str(closest["slope"])[:7]}, angle: {str(closest["angle"])[:7]}"
                geom = shape(closest["osm"]["geometry"])
                pname = str()
                if "name" in entry["properties"]:
                    pname = entry["properties"]["name"]
                sname = str()
                if "name" in props:
                    sname = props["name"]
                # if pname == "Twin Mountain Road":
                #     breakpoint()

                # print(f"ADDING: {pname} == {sname} dist: {str(closest["dist"])[:7]}, name: {closest["name_ratio"]}, ref: {closest["ref_ratio"]}, hits: {closest["hits"]}")
                # if hits >= 1:
                data.append(Feature(geometry=geom, properties=tags))
                # else:
                #     data.append(Feature(geometry=segment["geometry"], properties=tags))

            # data.append(Feature(geometry=geom, properties=tags))
            # If no hits, it's new data. ODK data is always just a POI for now
        elif hits == 0 and dist <= threshold:
            entry["properties"]["version"] = 1
            entry["properties"]["informal"] = "yes"
            entry["properties"]["fixme"] = "New features should be imported following OSM guidelines."
            entry["properties"]["debug"] = f"hits: {hits}, dist: {str(dist)[:7]}"
            # entry["properties"]["slope"] = slope
            # entry["properties"]["dist"] = dist
            # log.debug(f"FOO({dist}): {entry}")
            newdata.append(entry)

        # timer.stop()

    # log.debug(f"OLD: {len(data)}")
    # log.debug(f"NEW: {len(newdata)}")
    return [data, newdata]

class Conflator(object):
    def __init__(self,
                 uri: str = None,
                 boundary: str = None
                 ):
        """
        Initialize Input data sources.

        Args:
            uri (str): URI for the primary database
            boundary (str, optional): Boundary to limit SQL queries

        Returns:
            (Conflator): An instance of this object
        """
        self.postgres = list()
        self.tags = dict()
        self.boundary = boundary
        self.dburi = uri
        self.primary = None
        if boundary:
            infile = open(boundary, 'r')
            self.boundary = geojson.load(infile)
            infile.close()
        # Distance in meters for conflating with postgis
        self.tolerance = 7
        self.data = dict()
        self.analyze = ("building", "name", "amenity", "landuse", "cuisine", "tourism", "leisure")

    def getSlope(self,
            newdata: Feature,
            olddata: Feature,
            ) -> float:

        # timer = Timer(text="getSlope() took {seconds:.0f}s")
        # timer.start()
        # old = numpy.array(olddata["geometry"]["coordinates"])
        # oldline = shape(olddata["geometry"])
        angle = 0.0
        # newline = shape(newdata["geometry"])
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:3857')
            )
        newobj = transform(project.transform, shape(newdata["geometry"]))
        oldobj = transform(project.transform, shape(olddata["geometry"]))
        # if newline.type == "MultiLineString":
        #     lines = newline.geoms
        # elif newline.type == "GeometryCollection":
        #     lines = newline.geoms
        # else:
        #     lines = MultiLineString([newline]).geoms
        bestslope = None
        bestangle = None
        for segment in [newobj]:
            #new = numpy.array(newdata["geometry"]["coordinates"])
            #newline = shape(newdata["geometry"])
            points = shapely.get_num_points(segment)
            if points == 0:
                return -0.1, -0.1
            offset = 2
            # Get slope of the new line
            start = shapely.get_point(segment, offset)
            if not start:
                return float(), float()
            x1 = start.x
            y1 = start.y
            end = shapely.get_point(segment, points - offset)
            x2 = end.x
            y2 = end.y
            # if start == end:
            #     log.debug(f"The endpoints are the same!")
                # return 0.0, 0.0
            slope1 = (y2 - y1) / (x2 - x1)

            # Get slope of the old line
            start = shapely.get_point(oldobj, offset)

            if not start:
                return float(), float()
            x1 = start.x
            y1 = start.y
            end = shapely.get_point(oldobj, shapely.get_num_points(oldobj) - offset)
            x2 = end.x
            y2 = end.y
            # if start == end:
            #     log.debug(f"The endpoints are the same!")
                # return 0.0, 0.0

            if (x2 - x1) == 0.0:
                return 0.0, 0.0
            slope2 = (y2 - y1) / (x2 - x1)
            # timer.stop()
            slope = slope1 - slope2

            # Calculate the angle between the linestrings
            angle = math.degrees(math.atan((slope2-slope1)/(1+(slope2*slope1))))
            name1 = "None"
            name2 = "None"
            if math.isnan(angle):
                angle = 0.0
            if "name" in newdata["properties"]:
                name1 = newdata["properties"]["name"]
            if "name" in olddata["properties"]:
                name2 = olddata["properties"]["name"]
            try:
                if math.isnan(slope):
                    slope = 0.0
                if math.isnan(angle):
                    angle = 0.0

                # Find the closest segment
                if bestangle is None:
                    bestangle = angle
                elif angle < bestangle:
                    print(f"BEST: {best} < {dist}")
                    bestangle = angle
            except:
                print("BREAK")
                breakoint()

        return slope, bestangle # angle
      
    def getDistance(self,
            newdata: Feature,
            olddata: Feature,
            ) -> float:
        """
        Compute the distance between two features in meters

        Args:
            newdata (Feature): A feature from the external dataset
            olddata (Feature): A feature from the existing OSM dataset

        Returns:
            (float): The distance between the two features
        """
        # timer = Timer(text="getDistance() took {seconds:.0f}s")
        # timer.start()
        # dist = shapely.hausdorff_distance(center, wkt)
        dist = float()

        # Transform so the results are in meters instead of degress of the
        # earth's radius.
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:3857')
            )
        newobj = transform(project.transform, shape(newdata["geometry"]))
        oldobj = transform(project.transform, shape(olddata["geometry"]))

        # FIXME: we shouldn't ever get here...
        if oldobj.type == "MultiLineString":
            log.error(f"MultiLineString unsupported!")
            # FIXME: this returns a MultiLineString, so nee to track down why
            newline = linemerge(oldobj)

        if newobj.type == "MultiLineString":
            lines = newobj.geoms
        elif newobj.type == "GeometryCollection":
            lines = newobj.geoms
        else:
            lines = MultiLineString([newobj]).geoms

        # dists = list()
        best = None
        size_threshold = 0
        diff = newobj.length - oldobj.length
        # FIXME: this is just for current debug
        if abs(diff) > 1000:
            if "ref:usfs" in olddata["properties"]:
                name = olddata["properties"]["ref:usfs"]
            else:
                name = "n/a"
            # log.error(f"Large difference in highway lengths! {abs(diff)} {name}")

            oldpoly = oldobj.convex_hull
            inold = oldpoly.dwithin(newobj, size_threshold)
            newpoly = oldobj.convex_hull
            innew = newpoly.dwithin(oldobj, size_threshold)
            # print(f"IN: {inold} vs {innew}")
            if inold and innew:
                # print(f"ID: {olddata["properties"]["id"]}")
                return 0.0
            else:
                # if inold or innew:
                # print(f"ID: {olddata["properties"]["id"]}")
                # This is the only time a negative distance is returned !
                return -1.0
            # else:
            #     return 12345678.9

        for segment in lines:
            if oldobj.geom_type == "LineString" and segment.geom_type == "LineString":
                # Compare two highways
                # if oldobj.within(segment):
                #    log.debug(f"CONTAINS")
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "Point" and segment.geom_type == "LineString":
                # We only want to compare LineStrings, so force the distance check
                # to be False
                log.error(f"Unimplemented")
                dist = 12345678.9
            elif oldobj.geom_type == "Point" and segment.geom_type == "Point":
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "Polygon" and segment.geom_type == "Polygon":
                log.error(f"Unimplemented")
                # compare two buildings
                pass
            elif oldobj.geom_type == "Polygon" and segment.geom_type == "Point":
                # Compare a point with a building, used for ODK Collect data
                center = shapely.centroid(oldobj)
                dist = segment.distance(center)
            elif oldobj.geom_type == "Point" and segment.geom_type == "LineString":
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "LineString" and segment.geom_type == "Point":
                dist = segment.distance(oldobj)

            # Find the closest segment
            if best is None:
                best = dist
            elif dist < best:
                # log.debug(f"BEST: {best} < {dist}")
                best = dist

        # timer.stop()
        return best # dist # best

    def checkTags(self,
                  extfeat: Feature,
                  osm: Feature,
                   ):
        """
        Check tags between 2 features.

        Args:
            extfeat (Feature): The feature from the external dataset
            osm (Feature): The result

        Returns:
            (int): The number of tag matches
            (dict): The updated tags
        """
        match_threshold = 80
        match = ["name", "ref", "ref:usfs"]
        keep = ["UT", "CR", "WY", "CO", "US"]
        hits = 0
        props = dict()
        id = 0
        version = 0
        props = extfeat['properties'] | osm['properties']
        props["name_ratio"] = 0
        props["ref_ratio"] = 0

        # ODK Collect adds these two tags we don't need
        if "title" in props:
            del props["title"]
        if "label" in props:
            del props["label"]

        if "id" in props:
            # External data not from an OSM source always has
            # negative IDs to distinguish it from current OSM data.
            id = int(props["id"])
        else:
            id -= 1
            props["id"] = id

        if "version" in props:
            # Always use the OSM version if it exists, since it gets
            # incremented so JOSM see it's been modified.
            props["version"] = int(version)
            # Name may also be name:en, name:np, etc... There may also be
            # multiple name:* values in the tags.
        else:
            props["version"] = 1

        # These are all the other tags
        # if key not in match:
        #     pass

        # These tags require more careful checking
        for key in match:
            if "highway" in osm["properties"]:
                # Always use the value in the secondary, which is
                # likely OSM.
                props["highway"] = osm["properties"]["highway"]
            if key not in props:
                continue

            # In OSM, there may be an existing value for the ref
            # that is a county or state designation in addition to
            # the USFS reference number. That should be kept.
            if key == "ref" and osm["properties"]["ref"][:2] in keep:
                props["ref"] = osm["properties"]["ref"]
                continue

            # Usually it's the name field that has the most variety in
            # in trying to match strings. This often is differences in
            # capitalization, singular vs plural, and typos from using
            # your phone to enter the name. Course names also change
            # too so if it isn't a match, use the new name from the
            # external dataset.
            if key in osm["properties"] and key in extfeat["properties"]:
                length = len(extfeat["properties"][key]) - len(osm["properties"][key])
                # Sometimes there will be a word match, which returns a
                # ratio in the low 80s. In that case they should be
                # a similar length.
                ratio = fuzz.ratio(extfeat["properties"][key].lower(), osm["properties"][key].lower())
                # print(f"\tChecking ({key}:{ratio}): \'{extfeat["properties"][key].lower()}\', \'{osm["properties"][key].lower()}\'")
                if key == "name":
                    props["name_ratio"] = ratio
                else:
                    props["ref_ratio"] = ratio
                if ratio > match_threshold and length <= 3:
                    hits += 1
                    props[key] = extfeat["properties"][key]
                    if ratio != 100:
                        # Often the only difference is using FR or FS as the
                        # prefix. In that case, see if the ref matches.
                        if key[:3] == "ref":
                            # This assume all the data has been converted
                            # by one of the utility programs, which enfore
                            # using the ref:usfs tag.
                            tmp = extfeat["properties"]["ref:usfs"].split(' ')
                            exttype = tmp[0].upper()
                            extref = tmp[1].upper()
                            tmp = osm["properties"]["ref:usfs"].split(' ')
                            newtype = tmp[0]
                            newref = tmp[1].upper()
                            # print(f"\tREFS: {newtype} - {extref} vs {newref}: {extref == newref}")
                            if extref == newref:
                                hits += 1 
                                # Many minor changes of FS to FR don't require
                                # caching the exising value as it's only the
                                # prefix that changed. It always stays in this
                                # range.
                                if osm["properties"]["ref:usfs"][:3] == "FS " and ratio > 80 and ratio < 90:
                                    # log.debug(f"Ignoring old ref {osm["properties"]["ref:usfs"]}")
                                    continue
                        # For a fuzzy match, cache the value from the
                        # primary dataset and use the value in the
                        # secondary dataset since sometims the name in OSM is
                        # what  the highway is generally called, which at times
                        # may be greatly different from the official name.
                elif key == "name" and ratio > 0:
                        props["name"] = osm["properties"][key]
                        props["alt_name"] = extfeat["properties"]["name"]

        # print(props)
        return hits, props

    def conflateData(self,
                    primaryspec: str,
                    secondaryspec: str,
                    threshold: float = 10.0,
                    informal: bool = False,
                    ) -> list:
        """
        Open the two source files and contlate them.

        Args:
            primaryspec (str): The primary dataset filespec
            secondaryspec (str): The secondary dataset filespec
            threshold (float): Threshold for distance calculations in meters
            informal (bool): Whether to dump features in OSM not in external data

        Returns:
            (list):  The conflated output
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        odkdata = list()
        osmdata = list()

        result = list()
        # if odkspec[:3].lower() == "pg:":
        #     db = GeoSupport(odkspec[3:])
        #     result = await db.queryDB()
        # else:
        primarydata = self.parseFile(primaryspec)

        # if osmspec[:3].lower() == "pg:":
        #     db = GeoSupport(osmspec[3:])
        #     result = await db.queryDB()
        # else:
        secondarydata = self.parseFile(secondaryspec)

        entries = len(primarydata)
        chunk = round(entries / cores)

        alldata = list()
        newdata = list()
        tasks = list()

        # log.info(f"The primary dataset has {len(primarydata)} entries")
        # log.info(f"The secondary dataset has {len(secondarydata)} entries")
        if type(primarydata) == bool:
            log.error(f"The primary dataset, {primaryspec} has no features!")
            quit()
        else:
            print(f"The primary dataset has {len(primarydata)} entries")
        if type(secondarydata) == bool:
            log.error(f"The secondary dataset, {secondaryspec} has no features!")
            quit()
        else:
            print(f"The secondary dataset has {len(secondarydata)} entries")

        # Make threading optional for easier debugging
        if chunk == 0 or len(primarydata) < cores:
            single = True
        else:
            single = False

        # single = True          # FIXME: debug
        if single:
            alldata = conflateThread(primarydata, secondarydata)
        else:
            futures = list()
            with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
                for block in range(0, entries, chunk):
                    data = list()
                    future = executor.submit(conflateThread,
                            primarydata[block:block + chunk - 1],
                            secondarydata,
                            informal
                            )
                    futures.append(future)
                #for thread in concurrent.futures.wait(futures, return_when='ALL_COMPLETED'):
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    # log.debug(f"Waiting for thread to complete..,")
                    data.extend(res[0])
                    newdata.extend(res[1])
                alldata = [data, newdata]

            executor.shutdown()

        timer.stop()

        return alldata

    def dump(self):
        """
        Dump internal data for debugging.
        """
        print(f"Data source is: {self.dburi}")
        print(f"There are {len(self.data)} existing features")
        # if len(self.versions) > 0:
        #     for k, v in self.original.items():
        #         print(f"{k}(v{self.versions[k]}) = {v}")

    def parseFile(self,
                filespec: str,
                ) ->list:
        """
        Parse the input file based on it's format.

        Args:
            filespec (str): The file to parse

        Returns:
            (list): The parsed data from the file
        """
        path = Path(filespec)
        data = list()
        if path.suffix == '.geojson':
            # FIXME: This should also work for any GeoJson file, not
            # only  ones, but this has yet to be tested.
            log.debug(f"Parsing GeoJson files {path}")
            file = open(path, 'r')
            features = geojson.load(file)
            data = features['features']
        elif path.suffix == '.osm':
            log.debug(f"Parsing OSM XML files {path}")
            osmfile = OsmFile()
            data = osmfile.loadFile(path)
        elif path.suffix == ".csv":
            log.debug(f"Parsing csv files {path}")
            odk = ODKParsers()
            for entry in odk.CSVparser(path):
                data.append(odk.createEntry(entry))
        elif path.suffix == ".json":
            log.debug(f"Parsing json files {path}")
            odk  = ODKParsers()
            for entry in odk.JSONparser(path):
                data.append(odk.createEntry(entry))
        return data

    def conflateDB(self,
                     source: str,
                     ) -> dict:
        """
        Conflate all the data. This the primary interfacte for conflation.

        Args:
            source (str): The source file to conflate

        Returns:
            (dict):  The conflated features
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()

        log.info("Opening data file: %s" % source)
        toplevel = Path(source)
        if toplevel.suffix == ".geosjon":
            src = open(source, "r")
            self.data = geojson.load(src)
        elif toplevel.suffix == ".osm":
            src = open(source, "r")
            osmin = OsmFile()
            self.data = osmin.loadFile(source) # input file
            if self.boundary:
                gs = GeoSupport(source)
                # self.data = gs.clipFile(self.data)

        # Use fuzzy string matching to handle minor issues in the name column,
        # which is often used to match an amenity.
        if len(self.data) == 0:
            self.postgres[0].query("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
        # log.debug(f"OdkMerge::conflateData() called! {len(odkdata)} features")

        # A chunk is a group of threads
        chunk = round(len(self.data) / cores)

        # cycle = range(0, len(odkdata), chunk)

        # Chop the data into a subset for each thread
        newdata = list()
        future = None
        result = None
        index = 0
        if True:                # DEBUGGING HACK ALERT!
            result = conflateThread(self.data, self, index)
            return dict()

        with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
            i = 0
            subset = dict()
            futures = list()
            for key, value in self.data.items():
                subset[key] = value
                if i == chunk:
                    i = 0
                    result = executor.submit(conflateThread, subset, self, index)
                    index += 1
                    # result.add_done_callback(callback)
                    futures.append(result)
                    subset = dict()
                i += 1
            for future in concurrent.futures.as_completed(futures):
            # # for future in concurrent.futures.wait(futures, return_when='ALL_COMPLETED'):
                log.debug(f"Waiting for thread to complete..")
                # print(f"YYEESS!! {future.result(timeout=10)}")
                newdata.append(future.result(timeout=5))
        timer.stop()
        return newdata
        # return alldata

    def writeGeoJson(self,
                 data: dict,
                 filespec: str,
                 ):
        """
        Write the data to a GeoJson file.

        Args:
            data (dict): The list of GeoJson features
            filespec (str): The output file name
        """
        file = open(filespec, "w")
        fc = FeatureCollection(data)
        geojson.dump(fc, file, indent=4)

    def osmToFeature(self,
                     osm: dict(),
                     ) -> Feature:
        """
        Convert an entry from an OSM XML file with attrs and tags into
        a GeoJson Feature.

        Args:
            osm (dict): The OSM entry

        Returns:
            (Feature): A GeoJson feature
        """
        if "attrs" not in osm:
            return Feature(geometry=shape(osm["geometry"]), properties=osm["properties"])

        if "osm_id" in osm["attrs"]:
            id = osm["attrs"]["osm_id"]
        elif "id" in osm["attrs"]:
            id = osm["attrs"]["id"]
        props = {"id": id}
        if "version" in osm["attrs"]:
            props["version"] = osm["attrs"]["version"]

        props.update(osm["tags"])
        # It's a way, so no coordinate
        if "refs" in osm:
            return Feature(properties=props)
        else:
            geom = Point((float(osm["attrs"]["lon"]), float(osm["attrs"]["lat"])))

            return Feature(geometry=geom, properties=props)

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features in OSM.",
        epilog="""
This program conflates external datasets with OSM data. It can use a
postgres database, a GeoJson file, or any of all three ODK formats files
as the input sources. Some options are only used for greater control when
using a database. By default this uses the yaml based config files in the
osm-rawdata project, which are also used by the FMTM project. It is possible
to pass a custom SQL query, which if two databases are being conflated,
would apply to either.

        Examples:
                To conflate two files
         ./conflator.py -v -s camping-2024_06_14.osm -e extract.geojson

                To conflate a file using postgres
         ./conflator.py -v -s camping-2024_06_14.geojson -e PG:localhost/usa -b utah.geojson
        
The data extract file must be produced using the pgasync.py script in the
osm-rawdata project on pypi.org or https://github.com/hotosm/osm-rawdata.
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-s", "--secondary", help="The secondary dataset")
    parser.add_argument("-q", "--query", help="Custom SQL when using a database")
    parser.add_argument("-c", "--config", default="highway", help="The config file for the SQL query")
    parser.add_argument("-p", "--primary", required=True, help="The primary dataset")
    parser.add_argument("-t", "--threshold", default=2.0, help="Threshold for distance calculations")
    parser.add_argument("-i", "--informal", help="Dump features not in official sources")
    parser.add_argument("-o", "--outfile", default="conflated.geojson", help="Output file from the conflation")
    parser.add_argument("-b", "--boundary", help="Optional boundary polygon to limit the data size")

    args = parser.parse_args()
    indata = None
    source = None

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

    if not args.secondary and not args.uri:
        parser.print_help()
        log.error("You must supply a database URI or a data extract file!")
        quit()

    if args.query and args.config:
        parser.print_help()
        log.error("You must supply a either a conig file or custom SQL!")
        quit()

    outfile = None
    if args.outfile:
        outfile = args.outfile
    else:
        toplevel = Path(args.source)

    conflate = Conflator(args.secondary, args.boundary)
    # if args.secondary[:3].lower() == "pg:":
    #     await conflate.initInputDB(args.config, args.secondary[3:])

    # if args.primary[:3].lower() == "pg:":
    #     await conflate.initInputDB(args.config, args.secondary[3:])

    data = conflate.conflateData(args.primary, args.secondary, float(args.threshold), args.informal)

    # breakpoint()
    # path = Path(args.outfile)
    osmout  = args.outfile.replace(".geojson", "-out.osm")
    osm = OsmFile()
    osm.writeOSM(data[0], osmout)
    log.info(f"Wrote {osmout}")

    jsonout = args.outfile.replace(".geojson", "-out.geojson")
    conflate.writeGeoJson(data[0], jsonout)
    log.info(f"Wrote {jsonout}")

    jsonout = args.outfile.replace(".geojson", "-new.geojson")
    conflate.writeGeoJson(data[1], jsonout)

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
    #loop = asyncio.new_event_loop()
    #asyncio.set_event_loop(loop)
    #loop.run_until_complete(main())
