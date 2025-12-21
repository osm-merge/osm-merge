#!/usr/bin/python3

# Copyright (c) 2025 OpenStreetMap US
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

#
# This program proccesses the National Forest Service MVUM dataset. That
# processing includes deleting unnecessary tags, and converting the
# tags to an OSM standard for conflation.
#

import argparse
import logging
import sys
import os
import re
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
from thefuzz import fuzz, process
from pathlib import Path
from tqdm import tqdm
import tqdm.asyncio
from progress.bar import Bar, PixelBar
from osm_merge.yamlfile import YamlFile

import osm_merge as om
rootdir = om.__path__[0]

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class BLM(object):
    def __init__(self,
                 dataspec: str = None,
                 yamlspec: str = "utilities/blm.yaml",
                 ):
        """
        This class processes the dataset.

        Args:
            dataspec (str): The input data to convert
            yamlspec (str): The YAML config file for converting data

        Returns:
            (LocalRoads): An instance of this class
        """
        self.file = None
        if dataspec is not None:
            self.file = open(dataspec, "r")

        yaml = f"{rootdir}/{yamlspec}"
        if not os.path.exists(yaml):
            log.error(f"{yaml} does not exist!")
            quit()
        
        file = open(yaml, "r")
        self.yaml = YamlFile(f"{yaml}")

    def convert(self,
                filespec: str = None,
                ) -> list:

        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        spin = Bar('Processing...', max=len(data['features']))

        highways = list()
        suffix = str()
        config = self.yaml.getEntries()
        for entry in data["features"]:
            spin.next()
            geom = entry["geometry"]
            id = 0
            surface = str()
            name = str()
            if "PLAN_ASSET_CLASS" in entry:
                if entry["PLAN_ASSET_CLASS"].find("Trail") > 0:
                    suffix = "Road"
                else:
                    suffix = "Trail"
            props = {"highway": "unclassified"}
            for key, value in entry["properties"].items():
                # Don't convert all fields
                if key not in config["tags"]:
                    continue
                # ignore various bad entries
                if value is None:
                    continue
                if len(value.strip()) == 0:
                    continue
                # log.debug(f"{key} = {value}")
                # These keywords only have a single value
                if type(config["tags"][key]) == str():
                    if config["tags"][key][value].find('=') > 0:
                        tmp = config["tags"][key][value].split('=')
                        if len(tmp) > 1:
                            props[tmp[0]] = tmp[1]
                        continue

                if value.lower() == "unnamed" or value is None:
                    continue
                if config["tags"][key] == "ref":
                    if "BLM" in value:
                        props["ref"] = f"{value.replace("Rd. ", '')}"
                    else:
                        props["ref"] = f"BLM {value}"
                    continue
                if config["tags"][key] == "operator":
                    props["operator"] =  config["tags"]["operator"][value]
                if config["tags"][key] == "surface":
                    props["surface"] =  config["tags"]["surface"][value]

                if config["tags"][key] == "name":
                    # The name field values are inconsistent, sometimes starting with a
                    # number, then a colon, and then the name followed by "USGS" garbage.
                    # Other values start with BLM, aznd a colon, followed by the road
                    # name but without the USGS trailer.
                    colon = value.find(':')
                    if colon > 0:
                        props["ref"] = value[:colon]
                        props["name"] = f"{value[colon + 1:].title()}"
                        pos = props["name"].lower().find("usgs")
                        if pos > 0:
                            props["name"] = props["name"][:pos].title()
                    elif value.isnumeric():
                        props["ref"] = value.upper()
                    else:
                        if value.find("BLM") >= 0:
                            props["ref"] = value
                        else:
                            props["name"] = value.title()

                    # Expand abbreviations
                    if "name" in props:
                        for word in props["name"].split(' '):
                            if word.upper() in config["abbreviations"]:
                                abbrev = config["abbreviations"][word.upper()]
                                props["name"] = props["name"].replace(word, abbrev)
                    if "ref" in props and props["ref"].find("BLM") < 0:
                        props["ref"] = f"BLM {props["ref"].upper()}"
                    if "name" in props and props["name"].lower().find("road") <= 0:
                        if props["name"].lower().find("trail") <= 0:
                            props["name"] = f"{props["name"].strip()} Road"

                    if "name" in props:
                        pos = props["name"].rfind("Ohv Trail")
                        if pos > 0 and "ref" not in props:
                            props["ref"] =  f"BLM {props["name"][pos + 10:].upper()}"
                            props["highway"] = "track"
                        # if "Trail" in props["name"]:
                        #     pos = props["name"].rfind(' ')
                        #     ref = props["name"][pos +1:]
                        #     if ref != "Trail" and ref != "Trails":
                        #         props["ref"] = f"BLM {ref}"
                    if "alt_name" in props:
                        for word in props["alt_name"].split(' '):
                            if word.upper() in config["abbreviations"]:
                                new = config["abbreviations"][word.upper()]
                                props["name"] = props["alt_name"].replace(word,abbrev)
            if geom is not None:
                if "name" in props:
                    if props["name"].find("Trail") > 0:
                        props["highway"] = "path"
                    else:
                        props["highway"] = "unclassified"
                simple = shapely.simplify(shape(geom), tolerance=0.0001) # preserve_topology=True
                # Short roads may get simplified down to a single node.
                # In that case, use the original geometry.
                if shapely.count_coordinates(simple) <= 1:
                    highways.append(Feature(geometry=geom, properties=props))
                else:
                    highways.append(Feature(geometry=simple, properties=props))
                # print(props)

        return FeatureCollection(highways)
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="local-roads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts BLM road/trail into OSM",
        epilog="""
This program processes the state highway data. It will convert the 
dataset to using OSM tagging schema so it can be conflated. Abbreviations
are discouraged in OSM, so they are expanded. Most entries in the
dataset fields are ignored. There often isn't much here beyond state
nand county highway name, but it is another dataset.

    For Example: 
        local-roads.py -v --convert --infile LocalRoads.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Output file from the conflation")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert BLM feature to OSM feature")
    parser.add_argument("-o", "--outfile", default="out.geojson", help="Output file")

    args = parser.parse_args()

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

    roads = BLM()
    if args.convert and args.convert:
        data = roads.convert(args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file, indent=4)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
