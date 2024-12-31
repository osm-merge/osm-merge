#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024 OpenStreetMap US
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
from codetiming import Timer
from pathlib import Path
import osmium
from osmium.geom import WKBFactory, WKTFactory, GeoJSONFactory
import re
from shapely.geometry import shape
from shapely import prepare, from_geojson, from_wkt, contains, intersects, intersection, difference
from progress.spinner import Spinner
import geojson
# from osmium.filter import GeoInterfaceFilter

# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/

# Instantiate logger
log = logging.getLogger(__name__)

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts highways from OSM",
        epilog="""
This program extracts all the highways from an OSM file, and correct as
many of the bugs with names that are actually a reference number. 

    For Example: 
        osmhighways.py -v -i colorado-latest.osm.pbf -o co-highways.osm
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input directory")
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

    if not os.path.exists(args.infile):
        log.error(f"{args.infile} doesn't exist!")
        quit()

    infd = open(args.infile, 'r')
    data = geojson.load(infd)

    outfile = args.infile.replace(".geojson", ".poly")
    outfs = open(outfile, 'w')

    # First line is the file name
    index = 1
    outfs.write(f"{args.infile}\n")
    # log.debug(f"There are {len(data["features"])} features")
    if "features" in data:
        features = data["features"]
    else:
        features = [data]
    for poly in features:
        outfs.write(f"{index}\n")
        regions = poly["geometry"]["coordinates"]
        # log.debug(f"There is {len(regions)} coordinates {poly["geometry"]["type"]}")
        counter = 0
        if poly["geometry"]["type"] == "MultiPolygon":
            # It's a MultiPolygon if it has inners. The first
            # entry is the outer polygon, the rest are all inners.
            # We don't need the inners, just the outer.
            for coords in (poly["geometry"]["coordinates"][0][0]):
                outfs.write(f"    {coords[0]}   {coords[1]}\n")
                counter += 1
            outfs.write("END\n")
            index += 1
            continue
        elif poly["geometry"]["type"] == "Polygon":
            for coords in (poly["geometry"]["coordinates"][0]):
                outfs.write(f"    {str(coords[0])}   {str(coords[1])}\n")
                counter += 1
            outfs.write("END\n")
        elif poly["geometry"]["type"] == "LineString":
            # It's a LineString
            for coords in regions:
                if type(coords) == list:
                    outfs.write(f"    {coords[0]}   {coords[1]}\n")
                    continue
            # print(poly)
            outfs.write("END\n")
            index += 1

    outfs.write("END\n")
    # log.info("Wrote f{outfile} ...")
    
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
