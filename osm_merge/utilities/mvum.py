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
from osm_merge.yamlfile import YamlFile
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
# import geojson
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
import yaml
import fiona
import concurrent.futures
from datetime import datetime

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
# shut off verbose messages from fiona
logging.getLogger("fiona").setLevel(logging.WARNING)

def parse_opening_hours(datesopen: str) -> str:
    """
    Parse the string from the external dataset to OSM format.

    Args:
        datesopen (str): The string from the external dataset

    Returns:
        (str): The formatted string for OSM
    """
    months = {1: "Jan",
              2: "Feb",
              3: "Mar",
              4: "Apr",
              5: "May",
              6: "Jun",
              7: "Jul",
              8: "Aug",
              9: "Sep",
              10: "Oct",
              11: "Nov",
              12: "Dec",
              }
    opening_hours = str()
    # it's seasonal=no
    if not datesopen or datesopen == "01/01-12/31" or len(datesopen) < 11:
        return str()

    # Date ranges start with the first of the month, and end with
    # the last day of the month.
    dates = datesopen.split('-')
    start = dates[0].split('/')[0]
    try:
        end = dates[1].split('/')[0]
    except:
        breakpoint()
    try:
        opening_hours = f"{months[int(start)]}-{months[int(end)]}"
    except:
        breakpoint()
    return opening_hours

def processDataThread(config: dict,
                      # filespec: str,
                      data: list,
                      fixref: bool = True,
                      ) -> FeatureCollection:
    """
    Convert the Feature from the USFS schema to OSM syntax.

    """
    spin = Bar('Processing input data...', max=len(data))
    highways = list()

    for entry in data:
        spin.next()
        geom = entry["geometry"]
        props = dict()
        if geom is None:
            continue
        # FIXME: simplify the geometry with shapely.simplify

        exists = ["Drive", "Road", "Lane", "Circle"]
        # unclassified, as we don't know what it is.
        #        if "highway" not in props:
        props["highway"] = "unclassified"

        for key, value in entry["properties"].items():
            # print(f"FIXME: \'{key}\' = {value}")
            if key in config["tags"]["vehicle"]:
                props[key.lower()] = "designated"

            if key[-9:] == "DATESOPEN":
                if "opening_hours" not in props:
                    hours = parse_opening_hours(value)
                    # print(f"FIXME: {value} : {len(hours)}")
                    if len(hours) > 0:
                        props["opening_hours"] = hours
                        props["seasonal"] = "yes"
                    elif "opening_hours" in props:
                        props["seasonal"] = "no"
            if key not in config["tags"]:
                continue
            if config["tags"][key] == "name":
                if value:
                    # print(f"FIXME: \'{props}\' = {value.title()}")
                    newname = value.title()
                    words = newname.split(' ')
                    for word in words:
                        if word in config["abbreviations"]:
                            newname = newname.replace(word, config["abbreviations"][word])
                    # the ref is often duplicated in the name.
                    if "refs" in props and "name" in props:
                        if props["ref"] == props["name"]:
                            del props["name"]
                    # most of the names lack "Road" OSM prefers
                    props["name"] = newname.title()
            if config["tags"][key] == "smoothness":
                if value is None:
                    continue
                if value[:1].isnumeric():
                    # breakpoint()
                    if "smoothness" not in props:
                        for k, v in config["tags"]["smoothness"].items():
                            if k == value[:1]:
                                props["smoothness"] = v

                if len(value.strip()) == 0:
                    continue
                index = int(value[:1])
                if index >= 2:
                    props["4wd_only"] = "yes"
                for i in config["tags"]["smoothness"]:
                    if int(i) == index:
                        props["smoothness"] = config["tags"]["smoothness"][i]
            if config["tags"][key] == "seasonal":
                if value in config["tags"]["seasonal"]:
                    if bool(value):
                        props["seasonal"] = "no"
                    else:
                        props["seasonal"] = "yes"
            elif config["tags"][key] == "ref":
                if value is None:
                    continue
                if value.isnumeric() and fixref and len(value) == 5:
                    # FIXME: this fixes multiple forests in Utah and Colorado,
                    # don't know if any other states use a 5 digit reference
                    # number
                    # props["ref:orig"] = f"FR {value}"
                    props["ref"] = f"FR {value[1:]}"
                    # props["note"] = f"Validate this changed ref!"
                    # logging.debug(f"Converted {value} to {props["ref"]}")
                elif value.isalnum() and fixref:
                    # breakpoint()
                    pat = re.compile("[0-9]+")
                    result = re.match(pat, value)
                    # There are other patterns, like M21 for example
                    if not result:
                        props["ref"] = f"FR {value}"
                        continue

                    num = result.group()
                    if len(num) == 5:
                        # FIXME: Same here, but need to validate if 5 digit
                        # reference nunbers are used by some forests.
                        num = num[1:]
                    minor = value.find('.') > 0
                    if minor:
                        result = value.split('.')
                        newref = f"${num}.${result[1]}"
                    else:
                        alpha = value[len(num):]
                        newref = f"{num}{alpha}"

                    # props["ref:orig"] = f"FR {value}"
                    props["ref"] = f"FR {newref}"
                    # props["note"] = "Validate this changed ref!"
                else:
                    props["ref"] = f"FR {value}"

        if "name" in props and props["name"].find("Road") <= 0:
            props["name"] += " Road"
        if geom is not None:
            props["highway"] = "unclassified"
            highways.append(Feature(geometry=geom, properties=props))
        # print(props)

    return FeatureCollection(highways)

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

        filespec = f"{rootdir}/{yamlspec}"
        if not os.path.exists(filespec):
            log.error(f"{yamlspec} does not exist!")
            quit()

        yaml = YamlFile(filespec)
        # yaml.dump()
        self.config = yaml.getEntries()

    def count_lines(self, filespec: str) -> int:
        """
        Count the records in the data file.

        Args:
            filespec (str): The input data file name

        Returns:
            (int): The number of lines in the file
        """
        if not os.path.exists(filespec):
            logging.error(f"{filespec} doesn't exist!")
            return -1

        # data = fiona.open(filespec, "r")
        with fiona.open(filespec, 'r') as fp:
            for count, line in enumerate(fp):
                pass
            fp.close()
            return count

    def process_data(self,
                     filespec: str,
                     overwrite: bool,
                     usemem: bool = True,
                     tmpdir: str = "/tmp") -> list():
        """
        Read a large file in chunks so python stops core dumping.

        Args:
            filespec (str): The input data file name

        Returns:
            (list): The lines of data from the file
        """

        path = Path(filespec)
        lines = self.count_lines(path)
        if lines < 0:
            # logging.error(f"")
            return list()

        # Split the files into smaller chunks, one for each core.
        # FIXME: I hate tmp files, but disk space is better till
        # python stops core dumping on large files as the geojson
        # module loads the entire file into memory.
        size = round(lines / cores)

        data = fiona.open(filespec, "r")
        meta = data.meta
        files = list()
        single = True           # FIXME: debug only
        if not single:
            # with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            #     for block in range(0, size, chunk):
            #         data = list()
            #         future = executor.submit(processDataThread, self.conf,            )
            #         futures.append(future)
            #     #for thread in concurrent.futures.wait(futures, return_when='ALL_COMPLETED'):
            #     for future in concurrent.futures.as_completed(futures):
            #         res = future.result()
            #         # log.debug(f"Waiting for thread to complete..,")
            #         data.extend(res[0])
            #         # newdata.extend(res[1])
            #     alldata = [data, newdata]
            # return
            pass

        # single threaded for debugging
        if single:
            osmdata = processDataThread(self.config, list(data))

        # osmdata = list()
        # for i in range(0, lines, size):
        #     # Ignore the first output record, it's empty
        #     if i == 0:
        #         continue
        #     chunk = list()
        #     # dataout = f"{tmpdir}/{path.stem}_{i}.geojson"
        #     # files.append(dataout)
        #     # if os.path.exists(dataout):
        #     #    continue
        #     for record in iter(data):
        #         chunk.append(record)
        #         if len(chunk) == i:
        #             # for feature in chunk:
        #             #    alldata.append(feature)
        #             if not usemem:
        #                 dataout = f"{tmpdir}/{path.stem}_{i}.geojson"
        #                 out = fiona.open(dataout, 'w', **meta)
        #                 out.writerecords(chunk)
        #                 out.close()
        #                 logging.debug(f"Wrote tmp file {dataout}...")
        #             else:
        #                 if single:
        #                     osmdata.apppend(processDataThread(self.config, chunk))

        return osmdata

    def dump(self):
        """
        Dump internal variables for debugging.
        """
        for key, values in self.config:
            print(f"\t{k} = {values}")

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
        data = mvum.process_data(args.infile, False)
        # data = mvum.convert(args.infile)
        path = Path(args.outfile)
        if path.suffix == ".geojson":
            file = open(args.outfile, "w", encoding='utf-8',)
            # FIXME: should use fiona
            import geojson
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
