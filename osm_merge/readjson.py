#!/usr/bin/python3

# Copyright (c) 2024, 2025 OpenStreetMap US
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
import re
from sys import argv
from osm_merge.osmfile import OsmFile
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, Polygon, mapping
import shapely
from codetiming import Timer
from cpuinfo import get_cpu_info
from time import sleep
from pathlib import Path
from tqdm import tqdm
import asyncio
import tqdm.asyncio
import xmltodict
from numpy import arccos, array
from numpy.linalg import norm
import math
import numpy
import subprocess

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
# Try doubling the number of cores, since the CPU load is
# still reasonable.
cores = info['count']

class ReadGeojson(object):
    def __init__(self,
                 filespec: str = None,
                 read: bool = True,
                 ):
        self.file = None
        self.offset = 0
        self.size = 0
        if not filespec:
            log.error(f"You must supply a filename to read!")

        if read:
            self.file = open(filespec, "r")
            self.size = os.path.getsize(filespec)
        else:
            self.file = open(filespec, "w")

    def readFeatures(self,
                size: int,
                ) -> list:
        """
        Read features from the GeoJson file.

        Args:
            size (int): The number of features to read

        Returns:
            (list): of features
        """
        if not self.file:
            log.error(f"You must supply a filename to read!")
            return

        # Strip off the header
        if self.offset == 0:
            head = self.file.readline().strip()
            while head.find("features") <= 0:
                head = self.file.readline()

        self.offset += size
        # This is the actual start of the data
        line = self.file.readline().strip()

        # spin = Bar('Processing...', max=size)
        feature = str()
        props = dict()
        geom = None
        coords = str()
        features = list()
        closed = 0
        count = 0
        while len(line) > 0:
            # spin.next()
            if count == size:
                return features
            else:
                count += 1
            # newlines are only used between features
            if "properties" in line:
                start = line.find("properties") + 13
                end = line.find("},", start) + 1
                properties = line[start:end].replace("null", "None")
                props = eval(properties)

                if line.find("coordinates") <= 0:
                    # log.debug(f"Geometry is NULL!")
                    line = self.file.readline().strip()
                    continue
                start = line.find("coordinates") + 16
                end = line.find("}", start) - 4
                coords = line[start:end]
                lstr = list()
                for gps in coords.replace("[ ", "").split(" ], "):
                    tmp = gps.split(',')
                    try:
                        lstr.append([float(tmp[0]), float(tmp[1])])
                    except:
                        breakpoint()
                geom = LineString(lstr)
                features.append(Feature(geometry=geom, properties=props))
                continue
            else:
                print(line.strip())
                # if line == '{' or line == "{\n" or line.find("Feature") > 0:
                if line.find("Feature") > 0:
                    feature += line
                    line = self.file.readline().strip()
                    feature += line
                    props = dict()
                    continue
                elif line == '},' or line == "},\n":
                    # drop the trailing comma
                    feature += line[:-1]
                    # Get the properties
                    if len(props) == 0 and feature.find("geometry") <= 0:
                        props = eval(feature + '}')
                        feature = str()
                    elif len(props) > 0:
                        feature += line
                        print(feature)
                    line = self.file.readline().strip()
                    if geom is not None:
                        features.append(Feature(geometry=geom, properties=props))
                    continue
                else:
                    feature += line
                    line = self.file.readline().strip()
                continue
            # line = self.file.readline()

        #try:
        #    self.file.seek(self.offset)
        #except:
        #    log.error(f"Couldn't seek to {self.offset}")

        return features

    def writeFeatures(self,
                features: list(),
                ) -> bool:
        """
        Write features to a GeoJson file.

        Args:
            features (list): The features to write

        Returns:
            (bool): If it completed with no errors
        """
        out = str()
        # Add the header
        if self.offset == 0:
            self.file.write('{\n')
            self.file.write('"type": "FeatureCollection",\n')
            self.file.write('"name": "conflated",\n')
            # self.file.write('"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::4269" } },\n')
            self.file.write('"features": [\n')
            self.offset += len(features)

        for feature in features:
            self.file.write(f"{geojson.dumps(feature)},\n")

        return True

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program reads in a huge file in chunks",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-o", "--outfile", default="conflated.geojson", help="Output file")
    parser.add_argument("-i", "--infile", required=True, help="Input file")
    parser.add_argument("-s", "--size", default = 10000, help="Chunk Size")

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

    indata = ReadGeojson(args.infile)
    outdata = ReadGeojson(args.outfile, False)

    filesize = os.path.getsize(args.infile)
    if filesize > 0:
        lines = 372814
        # wc = subprocess.run(["/usr/bin/wc", "-l", args.infile],
        #                     shell = True,
        #                     capture_output = True,
        #                     text = True)
        # self.lines = int(wc.stdout.split(' ')[0])
        # log.debug(f"{self.lines} Lines in file")
    
        #pbar = tqdm.tqdm(primary)
        #spin = PixelBar('Processing...', max=lines)
        for features in range(0, filesize, args.size):
            features = indata.readFeatures(args.size)
            outdata.writeFeatures(features)
            #spin.next()

    log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
