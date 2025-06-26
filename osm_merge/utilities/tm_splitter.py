#!/bin/python3

# Copyright (c) 2024, 2025 OpenStreetMap US
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     FMTM-Splitter is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with FMTM-Splitter.  If not, see <https:#www.gnu.org/licenses/>.
#


"""
Class and helper methods for task splitting. Sort of like the HOT
Tasking Manager.
"""

# from tqdm import tqdm
# import tqdm.asyncio
from codetiming import Timer
from cpuinfo import get_cpu_info
from functools import partial
from geojson import Feature, FeatureCollection, GeoJSON
#from io import BytesIO
from math import ceil
from osgeo import ogr
from osgeo import osr
from pathlib import Path
import osmium
from osmium.geom import GeoJSONFactory
import fiona
from progress.spinner import Spinner
from shapely import contains, intersects, intersection
from psycopg2.extensions import connection
from shapely.geometry import Polygon, shape, LineString, MultiPolygon, box, shape, mapping, MultiLineString
from shapely.geometry.geo import mapping
from shapely.ops import split, transform, unary_union
# from shapely.prepared import prep
# from textwrap import dedent
import argparse
import asyncio
import geojson
import logging
import math
import numpy as np
import os
import shapely
import sys
import pyproj
from progress.bar import Bar, PixelBar

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

# shut off verbose messages from fiona
logging.getLogger("fiona").setLevel(logging.WARNING)

# Instantiate logger
log = logging.getLogger(__name__)

class TM_Splitter(object):
    def __init__(self, infile: str):
        """
        Args:
            infile (str): The input file to operate on

        Returns:
            (TM_SPlitter): An instance of this class
        """
        # infile is required, so will always be present
        self.infile = Path(infile)
        if not self.infile.exists():
            logging.error(f"{infile} does not exist!")
            quit()
        # Load the AOI

        file = self.infile.open()
        self.aoi = Path(infile)
        self.data = geojson.load(file)
        logging.debug(f"Loaded {infile}")
        file.close()

    def splitBySquare(self,
        aoi: FeatureCollection,
        meters: int,
        ) -> FeatureCollection:
        """Split the polygon into squares.

        Args:
            aoi (FeatureCollection): The project AOI
            meters (int):  The size of each task square in meters.

        Returns:
            data (FeatureCollection): A multipolygon of all the task boundaries.
        """
        log.debug("Splitting the AOI by squares")

        # We want to use meters, not degrees, so change the projection to do the
        # calculations.
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:3857')
        )
        newaoi = transform(project.transform, aoi)

        # xmin, ymin, xmax, ymax = aoi.bounds
        xmin, ymin, xmax, ymax = newaoi.bounds

        reference_lat = (ymin + ymax) / 2
        # 5000km square is roughly 0.44 degrees
        length_deg = meters # 0.44
        width_deg = meters # 0.44

        # Create grid columns and rows based on the AOI bounds
        cols = np.arange(xmin, xmax + width_deg, width_deg)
        rows = np.arange(ymin, ymax + length_deg, length_deg)

        extract_geoms = []

        # Generate grid polygons and clip them by AOI
        polygons = []
        for x in cols[:-1]:
            for y in rows[:-1]:
                grid_polygon = box(x, y, x + width_deg, y + length_deg)
                clipped_polygon = grid_polygon.intersection(newaoi)

                if clipped_polygon.is_empty:
                    continue

                # Check intersection with extract geometries if available
                if extract_geoms:
                    if any(geom.within(clipped_polygon) for geom in extract_geoms):
                        polygons.append(clipped_polygon)
                else:
                    polygons.append(clipped_polygon)

        tasks = list()
        index = 1
        # JOSM can't display EPSG:3857, so convert back to EPSG:4326 before writing
        # the geometry.
        newproj = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:3857'),
            pyproj.Proj(init='epsg:4326')
        )
        for poly in polygons:
            if poly.geom_type == 'MultiPolygon':
                # Many national forests have small polygons outside the main forest.
                # These are often visitor centers, and other buildings that we don't
                # care about, so filter them out of the final output file as the cause
                # issues with conflation.
                larger = list()
                for geom in poly.geoms:
                    if int(geom.area) >= 100000:
                        # log.debug(f"AREA: {foo.area}")
                        newgeom = transform(newproj.transform, geom)
                        larger.append(newgeom)
                new = MultiPolygon(larger)
                tasks.append(Feature(geometry=mapping(new), properties={"task": f"Task {index}"}))
            else:
                newpoly = transform(newproj.transform, poly)
                tasks.append(Feature(geometry=mapping(newpoly), properties={"task": f"Task {index}"}))
            index += 1

        return FeatureCollection(tasks)

    def make_grid(self,
                  meters: int
                  ):
        """
                  outfile: str,
        """
        if "features" in self.data:
            features = list()
            for feature in self.data["features"]:
                task = feature["geometry"]
                # Sometimes the geometry in the Administrative Boundaries
                # isn't always a good Polygon, or even MultiPolygon, so
                # construct a new MultiPolygon from all the geometries.
                if task.type == "LineString":
                    poly = Polygon(task["coordinates"])
                    features.append(poly)
                elif task.type == "MultiPolygon":
                    tasks = shape(feature["geometry"])
                    for poly in tasks.geoms:
                        features.append(poly)
            aoi = MultiPolygon(features)
        else:
            aoi = shape(self.data["geometry"])

        grid = self.splitBySquare(aoi, meters)

        return grid

    def make_tasks(self,
                   # data: FeatureCollection,
                   template: str,
                   ):
        """
        Make the task files, one for each polygon in the input file.

        Args:
            data (FeatureCollection): The input MultiPolygon to split into tasks
            outdir (str): Output directory for the output files
        """
        index = 1
        # Official datasets use a variety of name fields, find the one thats used
        names = ("NAME", "ADMU_NAME", "FORESTNAME", "NCA_NAME")
        for namefield in names:
            if namefield in self.data["features"][0]["properties"]:
                break
        if template.find('/') > 1:
            outdir = os.path.dirname(template)
            if not os.path.exists(outdir):
                os.mkdir(outdir)
        else:
            outdir = "./"
        # breakpoint()
        if "name" in self.data or namefield in self.data or namefield in self.data[0]["properties"]:
            spin = Bar('Processing...', max=len(self.data['features']))

            # Adminstriative boundaries use FeatureCollection
            for task in self.data["features"]:
                spin.next()
                geom = task["geometry"]
                if namefield in task["properties"]:
                    name = task["properties"][namefield].replace(" ", "_").replace(".", "").replace("-", "_").replace("/", "_").title()
                else:
                    try:
                        name = task["properties"]["PARENT_NAME"].replace(" ", "_").replace(".", "").replace("-", "_").replace("/", "_").title()
                    except:
                        continue
                        # breakpoint()
                outfile = f"{outdir}/{name}.geojson"
                fd = open(outfile, "w")
                if geom.type == 'LineString':
                    poly = Polygon(geom["coordinates"])
                else:
                    poly = geom
                feat = Feature(geometry=poly, properties= {"name": name})
                geojson.dump(feat, fd)
                # log.debug(f"Wrote {outfile}")
                fd.close()
        else:
            # The forest or park output files are a MultiPolygon feature
            index = 1
            # if template.find('/') > 1:
            #     if not os.path.exists(os.path.dirname(template)):
            #         os.mkdir(os.path.dirname(template))
            name = os.path.basename(template)
            for task in self.data["features"]:
                geom = shape(task["geometry"])
                outname = f"{template.replace('.geojson', '')}_{index}.geojson"
                if geom.type == 'Polygon':
                    fd = open(outname, "w")
                    properties = {"name": f"{name}_Task_{index}"}
                    feat = Feature(geometry=task, properties=properties)
                    geojson.dump(Feature(geometry=geom, properties=properties), fd)
                    log.debug(f"Wrote {outname}")
                    fd.close()
                    index += 1
                else:
                    if geom.type == 'LineString':
                        poly = Polygon(geom)
                        outname = f"{template.replace('.geojson', '')}_{index}.geojson"
                        fd = open(outname, "w")
                        properties = {"name": f"{name}_Task_{index}"}
                        geojson.dump(Feature(geometry=poly, properties=properties), fd)
                        log.debug(f"Wrote {outname}")
                        fd.close()
                        index += 1
                    elif geom.type == 'GeometryCollection' or geom.type == 'MultiPolygon':
                        for poly in geom.geoms:
                            if poly.type == 'LineString':
                                continue
                            outname = f"{template.replace('.geojson', '')}_{index}.geojson"
                            fd = open(outname, "w")
                            properties = {"name": f"{name}_Task_{index}"}
                            geojson.dump(Feature(geometry=poly, properties=properties), fd)
                            log.debug(f"Wrote {outname}")
                            fd.close()
                            index += 1

    def extract_data(self,
             infile: str,
             outfile: str,
             ) -> bool:
        """
        Extract the data from file.

        Args:
            infile (str): The input filename
            outfile (str): The output filename
        """
        path = Path(infile)
        if path.suffix == ".geojson":
            self.extract_external(infile, outfile)
        else:
            self.extract_osm(infile, outfile)

        return True

    def extract_external(self,
                         datain: str,
                         dataout: str,
                         ):
        """
        Extract data from a GeoJson file. This basically replicates using
        ogr2ogr -t_srs EPSG:4326 -makevalid -explodecollections.

        Args:
            datain (str):
            dataout (str):
        """
        aoi = fiona.open(self.aoi, 'r')
        polys = list()
        # Convert the boundary AOI to a clean list of Polygons
        spin = Spinner('Processing Task MultiPolygon file...')
        for task in aoi:
            spin.next()
            if task['geometry']['coordinates']:
                if task.geometry.type == "Polygon":
                    try:
                        polys.append(Polygon(task['geometry']['coordinates'][0]))
                    except:
                        logging.error(f"Bad task Polygon! {task.properties.get('name')}")
                        continue
                elif task.geometry.type == "MultiPolygon":
                    for poly in task.geometry.coordinates:
                        polys.append(Polygon(poly[0]))
                elif task.geometry.type == "LineString":
                    polys.append(Polygon(task['geometry']['coordinates']))

        logging.debug(f"There are {len(polys)} polygons in the boundary AOI")
        # input data
        data = fiona.open(datain)

        # output file
        meta = data.meta
        outfiles = dict()
        index = 0
        spin = Spinner('Processing input data...')
        dir = os.path.dirname(dataout)
        if len(dir) == 0:
            dir = "."
        for poly in polys:
            tmp =  dataout.split('.')[0]
            outdata = f"{tmp}_Task_{index}.geojson"
            # else: dataout = 
            outfiles[index] = {"task": index, "outfile": fiona.open(outdata, 'w', **meta), "geometry": poly}
            index += 1

        for feature in data:
            spin.next()
            if feature["geometry"] is None:
                continue
            if feature["geometry"]["type"] == "LineString":
                if len(feature["geometry"]["coordinates"]) <= 1:
                    continue
                geom = LineString(feature["geometry"]["coordinates"])
                for task, metadata in outfiles.items():
                    if geom.within(metadata["geometry"]) or geom.intersects(metadata["geometry"]):
                        # breakpoint()
                        metadata["outfile"].write(feature)
            elif feature["geometry"]["type"] == "MultiLineString":
                geom = MultiLineString(feature["geometry"]["coordinates"])
                for segment in geom.geoms:
                    for task, metadata in outfiles.items():
                        if geom.within(metadata["geometry"]):
                            # breakpoint()
                            metadata["outfile"].write(feature)

    def extract_osm(self,
             infile: str,
             outfile: str,
             ):
        """
        Clip the data in a file by a multipolygon instead of using
        the osmium command line program. The output file will only
        contain ways, in JOSM doing "File->update data' will load
        all the nodes so the highways are visible. It's slower of
        course than the osmium way, but this gives us better fine-grained
        control.

        Args:
            infile (str): The input data
            outfile (str): The output file

        Returns:filefile
            (bool): Whether it worked or not
        """
        timer = Timer(text="clip() took {seconds:.0f}s")
        timer.start()

        aoi = fiona.open(self.aoi, 'r')
        polys = list()
        # Convert the boundary AOI to a clean list of Polygons
        spin = Spinner('Processing Task MultiPolygon file...')
        for task in aoi:
            spin.next()
            if task['geometry']['coordinates']:
                if task.geometry.type == "Polygon":
                    try:
                        polys.append(Polygon(task['geometry']['coordinates'][0]))
                    except:
                        logging.error(f"Bad task Polygon! {task.properties.get('name')}")
                        continue
                elif task.geometry.type == "MultiPolygon":
                    for poly in task.geometry.coordinates:
                        polys.append(Polygon(poly[0]))
        logging.debug(f"There are {len(polys)} polygons in the boundary AOI")

        nodes = set()
        # Pre-filter the ways by tags. The less objects we need to look at, the better.
        way_filter = osmium.filter.KeyFilter('highway')
        # only scan the ways of the file
        spin = Spinner('Processing nodes...')
        dir = os.path.dirname(outfile)
        if len(dir) == 0:
            dir = "."

        index = 0
        outfiles = dict()
        path = Path(outfile)
        if outfile.find("Trail") > 0:
            otype = "Trails"
        else:
            otype = "Highways"
        for poly in polys:
            dataout = f"{dir}/OSM_{otype}_Task_{index}.osm"
            if os.path.exists(dataout):
                os.remove(dataout)
            writer = osmium.SimpleWriter(dataout)
            outfiles[index] = {"task": index, "outfile": writer, "geometry": poly}
            index += 1

        fp = osmium.FileProcessor(infile, osmium.osm.WAY).with_filter(osmium.filter.KeyFilter('highway'))
        for obj in fp:
            spin.next()
            if "highway" in obj.tags:
                nodes.update(n.ref for n in obj.nodes)

        # We need nodes and ways in the second pass.
        fab = GeoJSONFactory()
        spin = Spinner(f"Processing ways...")
        # FIXME: make this multi-threaded.
        way_filter = osmium.filter.KeyFilter('highway').enable_for(osmium.osm.WAY)
        for obj in osmium.FileProcessor(infile, osmium.osm.WAY | osmium.osm.NODE).with_filter(way_filter).with_locations():
            spin.next()
            if obj.is_node() and obj.id in nodes:
                # We don't want POIs for barrier or crossing, just LineStrings
                if len(obj.tags) > 0:
                    continue
                wkt = fab.create_point(obj)
                geom = shape(geojson.loads(wkt))
                # Add a node if it exists within the boundary
                for task, metadata in outfiles.items():
                    if contains(metadata["geometry"], geom) or intersects(metadata["geometry"], geom):
                        # breakpoint()
                        metadata["outfile"].add(obj)
                        # log.debug(f"Adding {obj.id}")
                        continue
                # Strip the object of tags along the way
                # writer.add_node(obj.replace(tags={}))
            # elif obj.is_way() and "highway" in obj.tags:
            elif obj.is_way():
                wkt = fab.create_linestring(obj.nodes)
                geom = shape(geojson.loads(wkt))
                for task, metadata in outfiles.items():
                    if contains(metadata["geometry"], geom) or intersects(metadata["geometry"], geom):
                        # breakpoint()
                        # log.debug(f"Adding way {obj.id}")
                        metadata["outfile"].add_way(obj)
            # writer.close()
        timer.stop()
        return True

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="tm-splitter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program manages tasks splitting",
        epilog="""
        This program implements some HOT Tasking Manager style functions
for use in other programs. This can generate a grid of tasks from an
AOI, and it can also split the multipolygon of that grid into seperate
files to use for clipping with ogr2ogr.

To break up a large public land boundary, a threshold of 0.7 gives
us a grid of just under 5000 sq km, which is the TM limit.

	tm-splitter.py --grid --infile boundary.geojson 

To split the grid file file into tasks, this will generate a separate
file for each polygon within the grid. This file can then also be used
for clipping with other tools like ogr2ogr, osmium, or osmconvert.

	tm-splitter.py --split --infile tasks.geojson
"""
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose output")
    parser.add_argument("-i", "--infile", required=True,
                        help="The input dataset")
    parser.add_argument("-g", "--grid", action="store_true",
                        help="Generate the task grid")
    parser.add_argument("-s", "--split", default=False, action="store_true",
                        help="Split Multipolygon")
    parser.add_argument("-o", "--outfile", default="out.geojson",
                        help="Output filename template")
    parser.add_argument("-m", "--meters", default=50000, type=int,
                        help="Grid size in kilometers")
    parser.add_argument("-e", "--extract", help="Extract data for Tasks")

    args = parser.parse_args()
    indata = None
    source = None

    # if verbose, dump to the terminal.
    log_level = os.getenv("LOG_LEVEL", default="INFO")
    if args.verbose is not None:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format=("%(asctime)s.%(msecs)03d [%(levelname)s] " "%(name)s | %(funcName)s:%(lineno)d | %(message)s"),
        datefmt="%y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    tm = TM_Splitter(args.infile)
    
    if args.outfile.find('/') > 1:
        outdir = os.path.dirname(args.outfile)
        if not os.path.exists(outdir):
            os.mkdir(outdir)
    else:
        outdir = "./"

    # Split the large file of administrative boundaries into each
    # area so they can be used for clipping.
    if args.split:
        template = args.outfile
        tm.make_tasks(template)
    elif args.extract:
        # cachefile = os.path.basename(args.infile.replace(".pbf", ".cache"))
        # create_nodecache(args.infile, cachefile)
        if not args.infile:
            log.error(f"You must specify the input file!")
            parser.print_help()
            quit()

        data = tm.extract_data(args.extract, args.outfile)
        log.info(f"Wrote clipped file {args.outfile}")
        quit()
    elif args.grid:
        grid = tm.make_grid(args.meters)
        if not args.outfile:
            outfile = "tasks.geojson"
        else:
            outfile = "./" + args.outfile

        file = open(args.outfile, "w")
        data = geojson.dump(grid, file)
        log.debug(f"Wrote {outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
