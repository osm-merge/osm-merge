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
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, Polygon, mapping
import shapely
from shapely.ops import transform
import pyproj
import asyncio
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from thefuzz import fuzz, process
from pathlib import Path
from tqdm import tqdm
import tqdm.asyncio


# ogrmerge.py -single -o trails.shp VECTOR_*/Shape/Trans_TrailSegment.shp

# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/
# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# https://wiki.openstreetmap.org/wiki/United_States_roads_tagging#Tagging_Forest_Roads

class NPS(object):
    def __init__(self,
                 filespec: str = None,
                 ):
        self.file = None
        if filespec is not None:
            self.file = open(filespec, "r")

    def convert(self,
                state: str,
                filespec: str = None,
                ) -> list:
        """
        Convert the USGS topographical dataset to something that can
        be conflated. The dataset schema is pretty ugly, duplicate
        field names, abbreviations, etc... plus a shapefile truncates
        the field names.

        Args:
            filespec (str): The input dataset file
            state (str): The 2 letter state abbreviation

        """
        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        highways = list()
        for entry in data["features"]:
            geom = entry["geometry"]
            props = dict()
            if "MAPSOURCE" in entry["properties"]:
                props["source"] = entry["properties"]["MAPSOURCE"]
            if "TRLNAME" in entry["properties"]:
                props["name"] = entry["properties"]["TRLNAME"].title()
            if "TRLSURFACE" in entry["properties"]:
                props["surface"] = entry["properties"]["TRLSURFACE"].lower()
            if "SEASONAL" in entry["properties"]:
                props["seasonal"] = entry["properties"]["SEASONAL"].lower()

            if len(props) == 0 or geom is None:
                continue
            highways.append(Feature(geometry=geom, properties=props))

        return FeatureCollection(highways)

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts USGS datasets into OSM tagging",
        epilog="""

    For Example: 
        mvum.py -v -c -i WY_RoadsMVUM.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input directory")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert USGS feature to OSM feature")
    parser.add_argument("-s", "--state", default="CO", help="The state the dataset is in")
    parser.add_argument("-o", "--outfile", default="out.geojson", help="Output file")

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

    nps = NPS()
    if args.convert and args.convert:
        data = nps.convert(args.state, args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(main())
    main()
