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

#
# This program proccesses the National Park service and national Forest
# Service trail datasets. That processing includes deleting unnecessary
# tags, and converting the tags to an OSM standard for conflation.
#

import argparse
import logging
import sys
import os
import re
from sys import argv
from osm_merge.osmfile import OsmFile
from osm_merge.yamlfile import YamlFile
from osm_merge.utilities.dateutil import parse_opening_hours, count_lines
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, Polygon, mapping
import shapely
from shapely.ops import transform
import asyncio
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from thefuzz import fuzz, process
from pathlib import Path
from tqdm import tqdm
import tqdm.asyncio
import fiona
from progress.bar import Bar, PixelBar

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

def processDataThread(config: dict,
                      # filespec: str,
                      data: list,
                      fixref: bool = True,
                      ) -> FeatureCollection:
    """
    Convert the Feature from the NPS or USFS schema to OSM syntax.

    """
    spin = Bar('Processing input data...', max=len(data))
    highways = list()

    for entry in data:
        spin.next()
        geom = entry["geometry"]
        props = dict()
        # OBJECTID is only in the NPS dataset
        if "OBJECTID" in entry["properties"]:
            props["operator"] = "National Park Service"
        else:
            props["operator"] = "US Forest Service"
        props["highway"] = "path"
        if geom is None:
            # This is unfortunately common in the USFS dataset
            # logging.error(f"The entry has no geometry!")
            continue
        for key, value in entry["properties"].items():
            # In USFS Trail data, these are the types of backcountry
            # access types. Each one has four values, but we only need
            # one, since in OSM the value will only be "yes".
            if value == "N/A" or value is None or value == "Unknown":
                continue
            pat = re.compile(".*ACCPT_DISC")
            if pat.search(key):
                hours = parse_opening_hours(value)
                if len(hours) > 0:
                    props["seasonal"] = "yes"
                    props["opening_hours"] = hours
                for k2, v2 in config["tags"]["type"].items():
                    pat = re.compile(f".*{k2}.*")
                    if pat.search(key.lower()):
                        if v2.find('=') > 0:
                            tmp = v2.split('=')
                            props[tmp[0]] = tmp[1]
                        else:
                            if "OBJECTID" in entry["properties"]:
                                props[v2] = "yes"
                            else:
                                props[v2] = "designated"
            if key not in config["tags"]:
                continue
            # print(f"FIXME: \'{key}\' = {value}")
            if config["tags"][key] == "name":
                # Seems obvious if there is no name, so drop it. The ref will
                # be enough to identify the trail.
                if value == "Un-Named" or len(value.strip()) == 0 or value is None:
                    continue
                words = value.split(' ')
                newname = value
                for word in words:
                    if word in config["abbreviations"]:
                        newname = newname.replace(word, config["abbreviations"][word])
                if newname.title().find(" Trail") > 0:
                    props["name"] = f"{newname.title()}"
                else:
                    props["name"] = f"{newname.title()} Trail"
            elif config["tags"][key] == "alt_name":
                if len(value.strip()) > 0:
                    # this is a bogus alternate name
                    if value == "Developed Area Trail":
                        continue
                    props["alt_name"] = value.title()
            elif config["tags"][key] == "ref":
                if "OBJECTID" in entry["properties"]:
                    props["ref"] = f"NPS {value}"
                else:
                    props["ref"] = f"FR {value}"
            # elif config["tags"][key] == "operator":
            #     if value == "RG-NPS":
            #         props["operator"] = "National Park Service"
            #     else:
            #         props["operator"] = value
            elif config["tags"][key] == "surface":
                pass
            elif config["tags"][key] == "seasonal":
                if value == "Yes":
                    props["seasonal"] = "yes"
                elif value == "No":
                    # props["seasonal"] = "no"
                    # This is the default, avoid tag bloat
                    pass
            elif config["tags"][key] == "access":
                # print(f"FIXME: {value}")
                for access in config["tags"]["access"]:
                    [[k2, v2]] = access.items()
                    pat = re.compile(f".*{k2}.*")
                    if pat.search(value.lower()):
                        if v2.find('=') > 0:
                            tmp = v2.split('=')
                            props[tmp[0]] = tmp[1]
                        else:
                            props[v2] = "yes"
                        # According to the OSM Wiki, these access types
                        # use highway=track instead of highway=path
                        if k2 in config["tags"]["highway"]:
                            props["highway"] = "track"

        simple = shapely.simplify(shape(geom), tolerance=0.0001) # preserve_topology=True
        # Short trails may get simplified down to a single node.
        # In that case, use the original geometry.
        if shapely.count_coordinates(simple) <= 1:
            highways.append(Feature(geometry=geom, properties=props))
        else:
            highways.append(Feature(geometry=simple, properties=props))

    return FeatureCollection(highways)

class Trails(object):
    def __init__(self,
                 dataspec: str = None,
                 yamlspec: str = "utilities/trails.yaml",
                 ):
        """
        This class processes the NPS and USFS Trails datasets.

        Args:
            dataspec (str): The input data to convert
            yamlspec (str): The YAML config file for converting data

        Returns:
            (Trails): An instance of this class
        """
        self.file = None
        if dataspec is not None:
            self.file = open(dataspec, "r")

        filespec = f"{rootdir}/{yamlspec}"
        if not os.path.exists(filespec):
            log.error(f"{yamlspec} does not exist!")
            quit()

        yaml = YamlFile(filespec)
        yaml.dump()
        self.config = yaml.getEntries()

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
        #lines = count_lines(filespec)
        #if lines < 0:
            # logging.error(f"")
        #    return list()

        # Split the files into smaller chunks, one for each core.
        # FIXME: I hate tmp files, but disk space is better till
        # python stops core dumping on large files as the geojson
        # module loads the entire file into memory.
        # size = round(lines / cores)

        data = fiona.open(filespec, "r")
        meta = data.meta
        files = list()
        single = True           # FIXME: debug only
        # single threaded for debugging
        if single:
            osmdata = processDataThread(self.config, list(data))
        else:
            logging.error(f"FIXME: multithreaded reader isn't implemented yet!")
        return osmdata
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="mvum",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts MVUM highway data into OSM tagging",
        epilog="""
This program processes the NPS and USFS trails datasets. It will convert
the data an OSM tagging schema so it can be conflated. Abbreviations are
discouraged in OSM, so they are expanded. Most entries in the two
dataset are ignored as they are blank. The schema is similar to the
MVUM schema, but not exactly.

    For Example: 
        trails.py -v -i NPS_-_Trails_-_Geographic_Coordinate_System.geojson -o NPS_Trails.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Output file from the conflation")
    # parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert MVUM feature to OSM feature")
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
    data = trails.process_data(args.infile, False)
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
        # osm.footer()
    log.info(f"Wrote {args.outfile}")
    # file = open(args.outfile, "w")
    # geojson.dump(data, file, indent=4)
    # log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
