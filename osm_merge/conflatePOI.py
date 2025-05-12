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
from sys import argv
from osm_merge.osmfile import OsmFile
from geojson import Feature, FeatureCollection, dump
import geojson
import concurrent.futures
import psycopg2
from shapely.geometry import shape, Point, Polygon, mapping
import shapely
from shapely import wkt
import xmltodict
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
from osm_merge.convert import escape
from osm_rawdata.postgres import uriParser, DatabaseAccess, PostgresClient
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from haversine import haversine, Unit
from thefuzz import fuzz, process
from geosupport import GeoSupport


# Instantiate logger
log = logging.getLogger("conflator")

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']


class ConflatePOI(object):
    def __init__(self,
                 dburi: str = None,
                 boundary: Polygon = None,
                 threshold: int = 7,
                 ):
        """
        This class conflates data that has been imported into a postgres
        database using the Underpass raw data schema.

        Args:
            dburi (str): The DB URI
            boundary (Polygon): The AOI of the project
            threshold (int): The distance in meters for distance calculations

        Returns:
            (ConflatePOI): An instance of this object
        """
        self.data = dict()
        self.db = None
        self.tolerance = threshold # Distance in meters for conflating with postgis
        self.boundary = boundary
        # Use a common select so it's consistent when parsing results
        self.select = "SELECT osm_id,tags,version,ST_AsText(geom),ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;%s\'))"
        if dburi:
            # for thread in range(0, cores + 1):
            self.db = GeoSupport(dburi)
            # self.db.append(db)
            # We only need to clip the database into a new table once
            if boundary:
                self.db.clipDB(boundary, self.db.db)
                self.db.clipDB(boundary, self.db.db, "nodes_view", "nodes")

    def overlaps(self,
                feature: dict,
                ):
        """
        Conflate a POI against all the features in a GeoJson file

        Args:
            feature (dict): The feature to conflate

        Returns:
            (dict):  The modified feature
        """
        # Most smartphone GPS are 5-10m off most of the time, plus sometimes
        # we're standing in front of an amenity and recording that location
        # instead of in the building.
        gps_accuracy = 10
        # this is the treshold for fuzzy string matching
        match_threshold = 80
        # log.debug(f"conflateFile({feature})")
        hits = False
        data = dict()
        geom = Point((float(feature["attrs"]["lon"]), float(feature["attrs"]["lat"])))
        wkt = shape(geom)
        for existing in self.data['features']:
            id = int(existing['properties']['id'])
            entry = shapely.from_geojson(str(existing))
            if entry.geom_type != 'Point':
                center = shapely.centroid(entry)
            else:
                center = entry
                # dist = shapely.hausdorff_distance(center, wkt)
                # if 'name' in existing['properties']:
                #     print(f"DIST1: {dist}, {existing['properties']['name']}")
            # x = shapely.distance(wkt, entry)
            # haversine reverses the order of lat & lon from what shapely uses. We
            # use this as meters is easier to deal with than cartesian coordinates.
            x1 = (center.coords[0][1], center.coords[0][0])
            x2 = (wkt.coords[0][1], wkt.coords[0][0])
            dist = haversine(x1, x2, unit=Unit.METERS)
            if dist < gps_accuracy:
                # if 'name' in existing['properties']:
                # log.debug(f"DIST2: {dist}")
                # log.debug(f"Got a Hit! {feature['tags']['name']}")
                for key,value in feature['tags'].items():
                    if key in self.analyze:
                        if key in existing['properties']:
                            result = fuzz.ratio(value, existing['properties'][key])
                            if result > match_threshold:
                                # log.debug(f"Matched: {result}: {feature['tags']['name']}")
                                existing['properties']['fixme'] = "Probably a duplicate!"
                                log.debug(f"Got a dup in file!!! {existing['properties']['name'] }")
                                hits = True
                                break
            if hits:
                version = int(existing['properties']['version'])
                # coords = feature['geometry']['coordinates']
                # lat = coords[1]
                # lon = coords[0]
                attrs = {'id': id, 'version': version, 'lat': feature['attrs']['lat'], 'lon': feature['attrs']['lon']}
                tags = existing['properties']
                tags['fixme'] = "Probably a duplicate!"
                # Data extracts for ODK Collect
                del tags['title']
                del tags['label']
                if 'building' in tags:
                    return {'attrs': attrs, 'tags': tags, 'refs': list()}
                return {'attrs': attrs, 'tags': tags}
        return dict()

    def queryToFeature(self,
                       results: list,
                       ):
        """
        Convert the results of an SQL to a GeoJson Feature

        Args:
            results (list): The results of the query

        Returns:
            (list): a list of the features fromn the results
        """

        features = list()
        for entry in results:
            osm_id = int(entry[0])
            tags = entry[1]
            version = int(entry[2])
            coords = shapely.from_wkt(entry[3])
            dist = entry[4]
            # ways have an additional column
            if len(entry) == 6:
                refs = entry[5]
            else:
                refs = list()
            if coords.geom_type == 'Polygon':
                center = shapely.centroid(coords)
                lat = center.y
                lon = center.x
                tags['geom_type'] = 'way'
            elif coords.geom_type == "Point":
                lat = coords.y
                lon = coords.x
                tags['geom_type'] = 'node'
            else:
                log.error(f"Unsupported geometry type: {coords.geom_type}")
            # match = entry[5] # FIXME: for debugging
            # the timestamp attribute gets added when it's uploaded to OSM.
            attrs = {'id': osm_id,
                    'version': version,
                    'lat': lat,
                    'lon': lon,
                    }
            tags['dist'] = dist
            # tags['match'] = match # FIXME: for debugging
            # tags['fixme'] = "Probably a duplicate node!"
            features.append({'attrs': attrs, 'tags': tags, 'refs': refs})

        return features

    def checkTags(self,
                  feature: Feature,
                  osm: dict,
                  ):
        """
        Check tags between 2 features.

        Args:
            feature (Feature): The feature from the external dataset
            osm (dict): The result of the SQL query

        Returns:
            (int): The nunber of tag matches
            (dict): The updated tags
        """
        tags = osm['tags']
        hits = 0
        match_threshold = 80
        if osm['tags']['dist'] > float(self.tolerance):
            return 0, osm['tags']
        for key, value in feature['tags'].items():
            if key in tags:
                ratio = fuzz.ratio(value, tags[key])
                if ratio > match_threshold:
                    hits += 1
                else:
                    if key != 'note':
                        tags[f'old_{key}'] = value
            tags[key] = value

        return hits, tags

    def conflateData(self,
                     data: list,
                     threshold: int = 7,
                     ):
        """
        Conflate all the data. This the primary interfacte for conflation.

        Args:
            data (list): A list of all the entries in the OSM XML input file
            threshold (int): The threshold for distance calculations

        Returns:
            (dict):  The modified features
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        # Use fuzzy string matching to handle minor issues in the name column,
        # which is often used to match an amenity.
        if len(self.data) == 0:
            self.db.queryDB("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
        log.debug(f"conflateData() called! {len(data)} features")

        # A chunk is a group of threads
        entries = len(data)
        chunk = round(len(data) / cores)

        if True: # FIXME: entries <= chunk:
            result = conflateThread(data, self)
            timer.stop()
            return result

        # Chop the data into a subset for each thread
        newdata = list()
        future = None
        result = None
        index = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
            i = 0
            subset = dict()
            futures = list()
            for key, value in data.items():
                subset[key] = value
                if i == chunk:
                    i = 0
                    result = executor.submit(conflateThread, subset, self)
                    index += 1
                    # result.add_done_callback(callback)
                    futures.append(result)
                    subset = dict()
                i += 1
            for future in concurrent.futures.as_completed(futures):
                log.debug(f"Waiting for thread to complete..")
                # print(f"YYEESS!! {future.result(timeout=10)}")
                newdata.append(future.result(timeout=5))
        timer.stop()
        return newdata

    def queryWays(self,
                    feature: Feature,
                    db: GeoSupport = None,
                    ):
        """
        Conflate a POI against all the ways in a postgres view

        Args:
            feature (Feature): The feature to conflate
            db (GeoSupport): The datbase connection to use

        Returns:
            (list): The data with tags added from the conflation
        """
        # log.debug(f"conflateWay({feature})")
        hits = 0
        result = list()
        geom = Point((float(feature["attrs"]["lon"]), float(feature["attrs"]["lat"])))
        wkt = shape(geom)

        # cleanval = escape(value)
        # Get all ways close to this feature.
#        query = f"SELECT osm_id,tags,version,ST_AsText(ST_Centroid(geom)),ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')) FROM ways_view WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')) < {self.tolerance} ORDER BY ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\'))"
        query = f"{self.select}" % wkt.wkt
        query += f", refs FROM ways_view WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')) < {self.tolerance} ORDER BY ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\'))"
        #log.debug(query)
        result = list()
        if db:
            result = db.queryDB(query)
        else:
            result = self.db.queryDB(query)
        if len(result) > 0:
            hits += 1
        else:
            log.warning(f"No results at all for {query}")

        return result

    def queryNodes(self,
                     feature: Feature,
                     db: GeoSupport = None,
                     ):
        """
        Find all the nodes in the view within a certain distance that
        are buildings or amenities.

        Args:
            feature (Feature): The feature to use as the location
            db (GeoSupport): The database connection to use

        Returns:
            (list): The results of the conflation
        """
        # log.debug(f"queryNodes({feature})")
        hits = 0
        geom = Point((float(feature["attrs"]["lon"]), float(feature["attrs"]["lat"])))
        wkt = shape(geom)
        result = list()
        ratio = 1

        # for key,value in feature['tags'].items():
        # print(f"NODE: {key} = {value}")
        # if key not in self.analyze:
        #     continue

        # Use a Geography data type to get the answer in meters, which
        # is easier to deal with than degress of the earth.
        # cleanval = escape(value)
        # query = f"SELECT osm_id,tags,version,ST_AsEWKT(geom),ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')),levenshtein(tags->>'{key}', '{cleanval}') FROM nodes_view WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')) < {self.tolerance} AND levenshtein(tags->>'{key}', '{cleanval}') <= {ratio}"
        # AND (tags->>'amenity' IS NOT NULL OR tags->>'shop' IS NOT NULL)"
        query = f"{self.select}" % wkt.wkt
        query += f" FROM nodes_view WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;{wkt.wkt}\')) < {self.tolerance} AND (tags->>'amenity' IS NOT NULL OR tags->>'building' IS NOT NULL)"
        #log.debug(query)
        # FIXME: this currently only works with a local database,
        # not underpass yet
        if db:
            result = db.queryDB(query)
        else:
            result = self.db.queryDB(query)
        # log.debug(f"Got {len(result)} results")
        if len(result) > 0:
            hits += 1
            # break
        # else:
        #     log.warning(f"No results at all for {query}")

        return result

def conflateThread(features: list,
                   cp: ConflatePOI,
                   ):
    """
    Conflate a subset of the data

    Args:
        features (list): The feature to conflate
        cp (ConflatePOI): The top level class

    Returns:
        (list): The results of the conflation
    """
    timer = Timer(text="conflateThread() took {seconds:.0f}s")
    timer.start()
    log.debug(f"conflateThread() called! {len(features)} features")
    result = dict()
    dups = 0
    # This is brute force, slow but accurate. Process each feature
    # and look for a possible match with existing data.
    merged = list()
    for key, value in features.items():
        id = int(value['attrs']['id'])
        geom = Point((float(value["attrs"]["lon"]), float(value["attrs"]["lat"])))
        if not shapely.contains(shape(cp.boundary), geom):
            # log.debug(f"Point is not in boundary!")
            continue
        # Each of the conflation methods take a single feature
        # as a parameter, and returns a possible match or a zero
        # length dictionary.
        results = list()
        if id > 0:
            # Any feature ID greater than zero is existing data.
            # Any feature ID less than zero is new data collected
            # using geopoint in the XLSForm.
            results = cp.queryById(value)
        elif id < 0:
            results = cp.queryNodes(value)
            if len(results) == 0:
                # log.warning(f"No results in nodes at all for {value}")
                results = cp.queryWays(value)
                if len(results) == 0:
                    log.warning(f"No results in ways at all for {value}")
                    # value['fixme'] = "Probably a new feature"
                    # merged.append(value)

        if len(results) == 0:
            merged.append(value)
            continue
            # log.error(f"There are no results!")

            # Merge the tags and attributes together, the OSM data and
            # data. If no match is found, the ODK data is used to
            # eate a new feature.
        if len(results) > 1:
            log.warning(f"Got more than one result! Got {len(results)}")

            for entry in cp.queryToFeature(results):
                hits, tags = cp.checkTags(value, entry)
                log.debug(f"Got {hits} out of {len(tags)} matched for {tags}")
                if hits > 0:
                    dups += 1
                    tags['fixme'] = f"Probably a duplicate, got {hits} matches"
                    entry['tags'] = tags
                    entry['attrs']['version'] += 1
                    merged.append(entry)
                    break
                else:
                    merged.append(value)

    timer.stop()
    log.debug(f"Found {dups} duplicates")
    return merged

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features from OSM.",
        epilog="""
    This program conflates external datasets with OSM data using a postgresql database.
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-o", "--osmuri", required=True, help="OSM Database URI")
    parser.add_argument("-t", "--threshold", default=7,
                        help="Threshold for distance calculations")
    parser.add_argument("-i", "--infile", required=True,
                        help="GeoJson or OSM XML file to conflate")
    parser.add_argument("-b", "--boundary",
                        help="Boundary polygon to limit the data size")

    args = parser.parse_args()
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

    outfile = os.path.basename(args.infile.replace('.osm', '-foo.osm'))

    # This is the existing OSM data, a database or a file
    file = open(args.boundary, 'r')
    boundary = geojson.load(file)
    if 'features' in boundary:
        poly = boundary['features'][0]['geometry']
    else:
        poly = boundary['geometry']
    extract = ConflatePOI(args.osmuri, poly, args.threshold)

    if extract:
        odkf = OsmFile(outfile)
        osm = odkf.loadFile(args.infile)
        #odkf.dump()
    else:
        log.error("No ODK data source specified!")
        parser.print_help()
        quit()

    # This returns a list of lists of dictionaries. Each thread returns
    # a list of the features, and len(data) is thre number of CPU cores.
    data = extract.conflateData(osm)
    out = list()
    #print(data)
    for entry in data:
        if 'geom_type' not in entry['tags']:
            if 'lat' in entry['attrs']:
                entry['tags']['geom_type'] = 'node'
        if entry['tags']['geom_type'] == 'way':
            del entry['tags']['geom_type']
            out.append(odkf.createWay(entry, True))
        else:
            del entry['tags']['geom_type']
            out.append(odkf.createNode(entry, True))
        # this isn't needed anymore

    odkf.write(out)
    log.info(f"Wrote {outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
