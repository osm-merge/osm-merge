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
import re
from sys import argv
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, MultiLineString, Polygon, mapping
import asyncio
from osm_merge.utilities.mvum import MVUM

import osm_merge as om
rootdir = om.__path__[0]

infile = "data/mvum-orig.geojson"
outfile = "data/mvum-osm.geojson"

def find_entry(data, key, value = None):
    """
    Find an entry in a FeatureCollection.

    Args:

    Returns:
        (list): The result data
    """
    result = list()
    for entry in data["features"]:
        for tag, val in entry ["properties"].items():
            if value and val:
                if tag.lower() == key and val.lower() == value:
                    return entry["properties"]
    return result
    
async def test_conversion():
    """
    This test must be run first as it create the output file other tests need.
    """
    logging.info("-- Running test_converstion() --")
    mvum = MVUM()
    if os.path.exists(outfile):
        os.remove(outfile)
    data = mvum.convert(infile)

    # Write the output file other tests need
    file = open(outfile, "w")
    geojson.dump(data, file, indent=4)
    logging.info(f"\nWrote {outfile}")
    
    assert len(data) > 0

async def test_syntax():
    """
    Test the syntax of the output file.
    """
    logging.info("-- Running test_syntax() --")

    if not os.path.exists(outfile):
        logging.error(f"Output file {outfile} i smissing!")
    file = open(infile, 'r')
    indata = geojson.load(file)
    file.close()

    file = open(outfile, 'r')
    outdata = geojson.load(file)
    file.close()

    # Get this highway
    orig = find_entry(indata, "name", "green divide")
    print(orig)

    new = find_entry(outdata, "name", "green divide")
    print(new)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    args = parser.parse_args()

    # if verbose, dump to the terminal.
    log_level = os.getenv("LOG_LEVEL", default="INFO")
    if args.verbose is not None:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        # format=("%(asctime)s.%(msecs)03d [%(levelname)s] " "%(name)s | %(funcName)s:%(lineno)d | %(message)s"),
        format=("[%(levelname)s] " "%(name)s | %(funcName)s:%(lineno)d | %(message)s"),
        datefmt="%y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    await test_conversion()
    await test_syntax()

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
