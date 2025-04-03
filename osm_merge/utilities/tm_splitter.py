#!/bin/python3

# Copyright (c) 2024 OpenStreetMap US
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
Class and helper methods for task splitting when working with the HOT
Tasking Manager since our projects are larger than 5000km area it
supports.
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
from progress.spinner import Spinner
from psycopg2.extensions import connection
from shapely.geometry import Polygon, shape, LineString, MultiPolygon, box, shape
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

# Instantiate logger
log = logging.getLogger(__name__)

def splitBySquare(
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
    # JOSM can't display epsg:3857, so convert back to epsg:4326 before writing
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

def make_tasks(data: FeatureCollection,
               template: str,
               ):
    """
    Make the task files, one for each polygon in the input file.

    Args:
        data (FeatureCollection): The input MultiPolygon to split into tasks
        outdir (str): Output directory for the output files
    """
    index = 1
    if template.find('/') > 1:
        outdir = os.path.dirname(template)
        if not os.path.exists(outdir):
            os.mkdir(outdir)
    else:
        outdir = "./"
    if "name" in data:
        # Adminstriative boundaries use FeatureCollection
        for task in data["features"]:
            geom = task["geometry"]
            if "FORESTNAME" in task["properties"]:
                name = task["properties"]["FORESTNAME"].replace(" ", "_").replace(".", "").replace("-", "_")
                outfile = f"{outdir}/{name}.geojson"
                fd = open(outfile, "w")
                feat = Feature(geometry=geom, properties= {"name": name})
                geojson.dump(feat, fd)
                log.debug(f"Wrote {outfile}")
                fd.close()
    else:
        # The forest or park output files are a MultiPolygon feature
        index = 1
        # if template.find('/') > 1:
        #     if not os.path.exists(os.path.dirname(template)):
        #         os.mkdir(os.path.dirname(template))
        name = os.path.basename(template)
        for task in data["features"]:
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

    args = parser.parse_args()
    indata = None
    source = None
    path = Path(args.infile)

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

    # The infile is either the the file to split, or the grid file.
    if not os.path.exists(args.infile):
        log.error(f"{args.infile} does not exist!")
        quit()

    # Load the AOI
    file = open(args.infile, "r")
    data = geojson.load(file)
    
    # Split the large file of administrative boundaries into each
    # area so they can be used for clipping.
    if args.split:
        template = args.outfile
        make_tasks(data, template)
    elif args.grid:
        # Generate the task grid
        if "features" in data:
            features = list()
            for feature in data["features"]:
                task = feature["geometry"]
                # Sometimes the geometry in the Administrative Boundaries isn't always
                # a good Polygon, or even MultiPolygon, so construct a new
                # MultiPolygon from all the geometries.
                if task.type == "LineString":
                    poly = Polygon(task["coordinates"])
                    features.append(poly)
                elif task.type == "MultiPolygon":
                    tasks = shape(feature["geometry"])
                    for poly in tasks.geoms:
                        features.append(poly)
            aoi = MultiPolygon(features)
        else:
            aoi = shape(data["geometry"])
        grid = splitBySquare(aoi, args.meters)
        if not args.outfile:
            outfile = "tasks.geojson"
        else:
            outfile = "./" + args.outfile

        if args.outfile.find('/') > 1:
            outdir = os.path.dirname(args.outfile)
            if not os.path.exists(outdir):
                os.mkdir(outdir)
        else:
            outdir = "./"

        file = open(args.outfile, "w")
        data = geojson.dump(grid, file)
        log.debug(f"Wrote {outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
