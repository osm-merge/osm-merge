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

#
# This program proccesses the National Park service trails dataset. That
# processing includes deleting unnecessary tags, and converting the
# tags to an OSM standard for conflation.
#

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
from progress.bar import Bar, PixelBar

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class Trails(object):
    def __init__(self,
                 filespec: str = None,
                 ):
        self.file = None
        if filespec is not None:
            self.file = open(filespec, "r")

    def convert(self,
                filespec: str = None,
                ) -> list:

        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        highways = list()
        spin = Bar('Processing...', max=len(data["features"]))
        for entry in data["features"]:
            spin.next()
            geom = entry["geometry"]
            props = dict()
            # These are the defaults for all trail features
            props["highway"] = "path"
            props["foot"] = "designated"
            props["bicyle"] = "no"
            props["motor_vehicle"] = "no"
            if "MAINTAINER" in entry["properties"]:
                # This is the NPS trail dataset
                props["operator"] = entry["properties"]["MAINTAINER"]
                if "TRLNAME" in entry["properties"]:
                    props["name"] = entry["properties"]["TRLNAME"]
                if "TRLALTNAME" in entry["properties"]:
                    if entry["properties"]["TRLALTNAME"] != "Unknown":
                        props["alt_name"] = entry["properties"]["TRLALTNAME"].title()
                if "TRLCLASS"  in entry["properties"]:
                    if entry["properties"]["TRLCLASS"] == "Class1":
                        pass
                    elif entry["properties"]["TRLCLASS"] == "Class2":
                        pass
                    elif entry["properties"]["TRLCLASS"] == "Class3":
                        pass
                    elif entry["properties"]["TRLCLASS"] == "Class4":
                        pass
                    elif entry["properties"]["TRLCLASS"] == "Class5":
                        pass
                if "TRLUSE" in entry["properties"]:
                    for usage in entry["properties"]["TRLUSE"].strip().split('|'):
                        if usage == "Unknown":
                            continue
                        elif usage == "Bike" or usage == "Bicycle":
                            props["bicycle"] = "yes"
                        elif usage == "ATV" or usage[:12] == "All-Terrain":
                            props["atv"] = "yes"
                        elif usage == "Motorcycle":
                            props["motorcycle"] = "yes"
                        elif usage == "ADA":
                            # FIXME on this tag
                            props["wheelchair"] = "yes"
                        elif usage.find("Saddle") > 0:
                            props["horse"] = "yes"
                        elif usage == "Bicycle/Motorized":
                            props["bicycle"] = "yes"
                            props["motor_vehicle"] = "yes"
                        elif usage == "Cross-Country Ski":
                            props["ski"] = "yes"
                        elif usage == "Dog Sled":
                            props["dog_sled"] = "yes"
                        elif usage == "Foot/Bicycle/Motorized":
                            props["bicycle"] = "yes"
                            props["motor_vehicle"] = "yes"
                        elif usage.find("Four-Wheel") > 0:
                            props["4wd_only"] = "yes"
                        elif usage == "Snowmobile":
                            props["snowmobile"] = "yes"
                        elif usage == "Snowshoe":
                            props["snowshoe"] = "yes"
                        elif usage == "Horse and Hiking" or usage == "Horse/Hiking":
                            props["horse"] = "yes"
                        elif usage == "Horse, Hiking, and Bicycle":
                            props["horse"] = "yes"
                            props["bicycle"] = "yes"
                        elif usage == "Horse/Motorized":
                            props["horse"] = "yes"
                            props["motor_vehicle"] = "yes"
                        elif usage == "Motorized":
                            props["motor_vehicle"] = "yes"
                        elif usage == "Wheelchair Accessible Trail":
                            props["wheelchair"] = "yes"
                    if "TRLSURFACE" in entry["properties"]:
                        types = ["metal",
                                 "rubber",
                                 "snow",
                                 "clay",
                                 "brick",
                                 "concrete",
                                 "asphalt",
                                 "wood",
                                 "sand",
                                 ]
                        surface = entry["properties"]["TRLSURFACE"].lower()
                        if surface[:7] == "gravel":
                            props["surface"] = "gravel"
                        elif surface == "Native":
                            props["surface"] = "ground"
                        elif surface == "earth" or surface == "dirt" or surface == "soil":
                            props["surface"] = "dirt"
                        elif surface == "Aggregate":
                            props["surface"] = "chipseal"
                        elif surface == "Bituminous":
                            props["surface"] = "asphalt"
                        elif surface in types:
                            # Catch everything in the list
                            props["surface"] = surface.lower()
                    if "SEASONAL" in entry["properties"]:
                        props["seasonal"] = "yes"

            else:
                # This is the USFS dataset
                spin.next()
                props["operator"] = "US Forest Service"
                id = 0
                sym = 0
                op = None
                surface = str()
                name = str()
                # props["informal"] = "no"
                # print(entry["properties"])
                for key, value in entry["properties"].items():
                    if value == "N/A" or value is None:
                        continue
                    # print(key, value)
                    if key == "TRAIL_NO":
                        id = f"FR {entry['properties']['TRAIL_NO']}"
                        # For consistency, capitalize the last character
                        props["ref:usfs"] = id.upper()

                    elif key == "TRAIL_NAME":
                        props["name"] = value.title()
                    if key[:-6] == "_ACCPT" and value == "Y":
                        value = "yes"
                    elif key[:-5] == "_DISC" and value == "Y":
                        value = "discouraged"
                    elif key[:-12] == "_ACCPT_DISC" and value == "Y":
                        value = "permissive"
                    elif key[:-9] == "_MANAGED" and value == "Y":
                        value = "designated"
                    elif key[:-11] == "_RESTRICTED" and value == "Y":
                        value = "no"
                    if key[:16] == "HIKER_PEDESTRIAN" and value == "Y":
                        props["foot"] = value
                    elif key[:11] == "SNOWMOBILE" and value == "Y":
                        props["snowmobile"] = value
                    elif key[:7] == "BICYCLE" and value == "Y":
                        props["bicyclMAINTAINERe"] = value
                    elif key[:3] == "ATV" and value == "Y":
                        props["atv"] = value
                    elif key[:10] == "MOTORCYCLE" and value == "Y":
                        props["motorcycle"] = value
                    elif key[:11] == "PACK_SADDLE" and value == "Y":
                        props["horse"] = "yes"
                    elif key[:8] == "SNOWSHOE" and value == "Y":
                        props["snowshoe"] = value
                    elif key[:13] == "XCOUNTRY_SKI" and value == "Y":
                        props["ski"] = value

            if geom is not None:
                highways.append(Feature(geometry=geom, properties=props))
            #print(props)

        return FeatureCollection(highways)
        
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="mvum",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts MVUM highway data into OSM tagging",
        epilog="""
This program processes the NPS trails dataset. It will convert the data
to using OSM tagging schema so it can be conflated. Abbreviations are
discouraged in OSM, so they are expanded. Most entries in the NPS
dataset are ignored. The schema is similar to the MVUM schema, but not
exactly.

    For Example: 
        trails.py -v -c -i /National_Park_Service_Trails.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Output file from the conflation")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert MVUM feature to OSM feature")
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

    trails = Trails()
    if args.convert and args.convert:
        data = trails.convert(args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file, indent=4)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
