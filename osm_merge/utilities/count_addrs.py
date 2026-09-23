#!/usr/bin/python3

# Copyright (c) 2025, 2026 OpenStreetMap US
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

import csv
import json
import logging
import os
import re
import sys
import argparse
from sys import argv
from pathlib import Path
import geojson
from geojson import Feature, FeatureCollection, GeometryCollection, LineString, MultiPolygon, Polygon
import re
from geomet import wkt
# from geojson import Point, Feature, FeatureCollection, LineString
from shapely.geometry import LineString, shape, Polygon
# from shapely.geometry.polygon import Polygon
import shapely
import psycopg2
from osm_merge.dbextract import DBExtract
from datetime import datetime
from tqdm import tqdm
import tqdm.asyncio
from osm_merge.yamlfile import YamlFile

# Instantiate logger
log = logging.getLogger(__name__)

import osm_merge as om
rootdir = om.__path__[0]


class CountAddrs(object):
    def __init__(self,
                yamlspec: str = "utilities/mvum.yaml",
                ):
        """

        Args:
            dataspec (str): The input data to convert
            yamlspec (str): The YAML config file for converting data

        Returns:
            (CountAddrs): An instance of this class
        """
        yaml = f"{rootdir}/{yamlspec}"
        if not os.path.exists(yaml):
            log.error(f"{yaml} does not exist!")
            quit()
        
        file = open(yaml, "r")
        self.yaml = YamlFile(f"{yaml}")

    def convert(self,
                name: str = None,
                ) -> list:
        """
        """
        config = self.yaml.getEntries()
        newname = str()
        newvalue = str()
        for word in name.split():
            # Fix some common abbreviations
            abbrevs = config["abbreviations"]
            if word in abbrevs:
                newvalue += abbrevs[word]
            else:
                newvalue += word
            newvalue += ' '

        return newvalue

def main():
    """
    This program queries a postgres database as maintained by Underpass.
    """
    parser = argparse.ArgumentParser(description="Query a DB and output to OSM XML format")
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-b","--boundary", help='Optional boundary to clip the data')
    parser.add_argument("-o","--outfile", default='out.geojson', help='The output file')
    parser.add_argument("-u", "--uri", help="Database URI")

    args = parser.parse_args()

    # Need at least one operation
    if len(argv) == 1:
        parser.print_help()
        quit()

    # if verbose, dump to the terminal
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )


    ca = CountAddrs()
    db = DBExtract(args.uri)
    
    # Make a temporary view to reduce the data size
    if args.boundary:
        db.create_view(args.boundary)
    else:
        db.create_view()

    # convert = Convert()

    # Query the database for what we want
    sql = f"SELECT osm_id,version,timestamp,refs,tags,ST_AsTEXT(geom) FROM "
    rows = db.execute_query(sql)
    highset = set()
    for highway in rows:
        tags = highway[4]
        # FIXME: only needed for non OSM data
        if "name" in tags:
            #     new = ca.convert(tags["name"])
            highset.add(tags["name"])

    if len(rows) == 0:
        log.error(f"No data returned from the query!")
        quit()
    features = db.filter_rows(rows)

    for name in sorted(highset):
        name = name.replace("'", "\"")
        sql = f"SELECT COUNT(tags) FROM nodes WHERE tags->>'addr:street' LIKE '{name}%' "
        result = db.execute_query(sql)
        if len(result) > 0:
            log.debug(f"{name} has {result[0][0]} addresses")
    
    # path = Path(args.outfile)
    # if path.suffix == ".geojson":
    #     log.debug(f"Writing data to GeoJson file, this make take awhile...")
    #     file = open(args.outfile, "w")
    #     geojson.dump(FeatureCollection(features), file, indent=2, default=str)
    #     file.close()
    #     log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
