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
from time import sleep
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

class MVUM(object):
    def __init__(self,
                 dataspec: str = None,
                 yamlspec: str = "utilities/mvum.yaml",
                 ):
        """
        This class processes the MVUM dataset.

        Args:
            dataspec (str): The input data to convert
            yamlspec (str): The YAML config file for converting data

        Returns:
            (MVUM): An instance of this class
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
                fixref: bool = True,
                ) -> list:

        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        spin = Bar('Processing input file...', max=len(data['features']))

        highways = list()
        config = self.yaml.getEntries()
        for entry in data["features"]:
            spin.next()
            geom = entry["geometry"]
            id = 0
            sym = 0
            op = None
            surface = str()
            name = str()
            props = dict()
            if "OPER_MAINT_LEVEL" in entry["properties"]:
                format = "RoadCore"
            else:
                format = "MVUM"
            # print(entry["properties"])
            if entry["properties"] is None or entry is None:
                continue
            if "ID" in entry["properties"]:
                id = f"FR {entry['properties']['ID']}"
                # For consistency, capitalize the last character
                props["ref"] = id.upper()
            if "NAME" in entry["properties"] and entry["properties"]["NAME"] is not None:
                title = entry["properties"]["NAME"].title()
                name = str()
                # Fix some common abbreviations
                for word in title.split():
                    category = config["columns"]["NAME"]
                    if word in config[category]:
                        name += config[category][word]
                    else:
                        name += f" {word} "
                if len(name) == 0:
                    name = title.title()
                newname = str()
                if name.find(" Road") <= 0:
                    newname = f"{name} Road".replace('  ', ' ').strip()
                else:
                    newname = name.replace('  ', ' ').strip()
                # the < causes osmium to choke...
                props["name"] = newname.replace("<50", "&lt;50")

            if format == "MVUM":
                keyword = "OPERATIONALMAINTLEVEL"
            else:
                keyword = "OPER_MAINT_LEVEL"
            # https://www.fs.usda.gov/Internet/FSE_DOCUMENTS/stelprd3793545.pdf
            if keyword in entry["properties"] and entry["properties"][keyword] is not None:
                if len(entry["properties"][keyword]) <= 1:
                    continue
                field = entry["properties"][keyword].split()[0]
                if field != "NA":
                    smoothness = config["tags"]["smoothness"][int(field)]
                    pair = smoothness.split('=')
                    props[pair[0]] = pair[1]
                    # High Clearance vehicles only
                    if int(field) == 2:
                        props["4wd_only"] = "yes"

            if "PRIMARY_MAINTAINER" in entry["properties"] and entry["properties"]["PRIMARY_MAINTAINER"]:
                field = entry["properties"]["PRIMARY_MAINTAINER"].split()[0]
                if field in config["tags"]["operator"]:
                    operator = config["tags"]["operator"][field]
                    props["operator"] = operator
                    # props["operator:type"] = "government"
            else:
                props["operator"] = "US Forest Service"

            if format == "MVUM":
                keyword = "SURFACETYPE"
            else:
                keyword = "SURFACE_TYPE"
            if keyword in entry["properties"] and entry["properties"][keyword]:
                if "surface" not in props:
                    # Only add a value for surface if it doesn't exist
                    if entry["properties"][keyword] == " ":
                        continue
                    field = entry["properties"][keyword].split()[0]
                    if field in config["tags"]["surface"]:
                        surface = config["tags"]["surface"][field]
                        pair = surface.split('=')
                        props[pair[0]] = pair[1]

            if format == "MVUM":
                keyword = "SBS_SYMBOL_NAME"
            else:
                keyword = "SYMBOL_NAME"
            if keyword in entry["properties"] and entry["properties"][keyword]:
                field = entry["properties"][keyword][:4]
                symbol = config["tags"]["symbol"][field]
                pair = symbol.split('=')
                props[pair[0]] = pair[1]
                if len(props["ref"].split()) <= 1:
                    continue
                ref = props["ref"].split()[1].replace(' ', '')
                minor = ref.find('.') > 0
                if ref.isnumeric() and fixref and len(ref) == 5:
                    # FIXME: this fixes multiple forests in Utah and Colorado,
                    # don't know if any other states use a 5 digit reference
                    # number
                    props["ref:orig"] = f"FR {ref}"
                    props["ref"] = f"FR {ref[1:]}"
                    props["note"] = f"Validate this changed ref!"
                    logging.debug(f"Converted {ref} to {props["ref"]}")
                elif ref.isalnum() and fixref and len(ref) == 5:
                    # breakpoint()
                    pat = re.compile("[0-9]+")
                    result = re.match(pat, ref)
                    # There are other patterns, like M21 for example
                    if not result:
                        props["ref"] = f"FR {ref}"
                        continue

                    num = result.group()
                    if len(num) == 5:
                        # FIXME: Same here, but need to validate if 5 digit
                        # reference nunbers are used by some forests.
                        num = num[1:]
                    if minor:
                        result = ref.split('.')
                        newref = f"FR ${num}.${result[1]}"
                    else:
                        alpha = ref[len(num):]
                        newref = f"FR {num}{alpha}"

                    props["ref:orig"] = f"FR {ref}"
                    props["ref"] = f"FR {newref}"
                    props["note"] = f"Validate this changed ref!"
                    # if newref != f"FR {ref}":
                    logging.debug(f"Converted {ref} to {newref}")
                else:
                    logging.debug(f"No conversion of FR {ref} needed")
                    props["ref"] = f"FR {ref}"

            if format == "MVUM":
                keyword = "HIGHCLEARANCEVEHICLE"
            else:
                keyword = "HIGH_CLEARANCE_VEHICLE"
            if keyword in entry["properties"] and entry["properties"][keyword]:
                if entry["properties"][keyword] is not None:
                    props["4wd_only"] = "yes"

            if "SEASONAL" in entry["properties"] and entry["properties"]["SEASONAL"]:
                    field = entry["properties"]["SEASONAL"]
                    if field in config["tags"]["seasonal"]:
                        seasonal = config["tags"]["seasonal"][field]
                        pair = seasonal.split('=')
                        props[pair[0]] = pair[1]

            if geom is not None:
                props["highway"] = "unclassified"
                highways.append(Feature(geometry=geom, properties=props))
            # print(props)

        return FeatureCollection(highways)
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="mvum",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts MVUM highway data into OSM tagging",
        epilog="""
This program processes the MVUM data. It will convert the MVUM dataset
to using OSM tagging schema so it can be conflated. Abbreviations are
discouraged in OSM, so they are expanded. Most entries in the MVUM
dataset are ignored. For fixing the TIGER mess, all that is relevant
are the name and the USFS reference number. The surface and smoothness
tags are also converted, but should never overide what is in OSM, as the
OSM values for these may be more recent. And the values change over time,
so what is in the MVUM dataset may not be accurate. These tags are converted
primarily as an aid to navigation when ground-truthing, since it's usually
good to avoid any highway with a smoothness of "very bad" or worse.

    For Example: 
        mvum.py -v -c -i WY_RoadsMVUM.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Output file from the conflation")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert MVUM feature to OSM feature")
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

    mvum = MVUM()
    if args.convert and args.convert:
        data = mvum.convert(args.infile)
        path = Path(args.outfile)
        if path.suffix == ".geojson":
            file = open(args.outfile, "w")
            geojson.dump(data, file, indent=4)
        elif path.suffix == ".osm":
            osm = OsmFile()
            osm.header()
            osm.writeOSM(data, args.outfile)
            osm.footer()
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
