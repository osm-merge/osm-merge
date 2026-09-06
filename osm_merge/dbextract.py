#!/usr/bin/python3

# Copyright (c) 2025, 2006 OpenStreetMap US
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
import asyncio
import argparse
from pathlib import Path
import geojson
from geojson import Feature, FeatureCollection, LineString
# from geojson import Point, Feature, FeatureCollection, LineString
from shapely.geometry import LineString, shape
import shapely
import psycopg2
from osm_merge.osmfile import OsmFile
from datetime import datetime
from tqdm import tqdm
import tqdm.asyncio

# Instantiate logger
log = logging.getLogger(__name__)

import osm_merge as om
rootdir = om.__path__[0]

class DBExtract(object):
    def __init__(self,
                uri: str,
                ) -> DBExtract:
        """
        Initialize the database connection

        Args:
            database (str): The database to use

        Returns:
            DBExtract: An instance of this class
        """
        self.curs = None
        self.db = None
        if uri:
            host = uri.split('/')[0]
            db = uri.split('/')[1]
            try:
                pargs = f"dbname={db}"
                if host != "localhost":
                    pargs+= f" host={host}"
                self.db = psycopg2.connect(pargs)
                self.curs = self.db.cursor()
                log.info(f"Connected to database {db} on {host}")
            except Exception as e:
                log.error(f"Couldn't connect to database: {e}")

    def create_view(self,
                    boundary: str = None,
                    ) -> bool:
        """
        Filter the data by a multi-polygon to reduce the size.

        Args:
            boundary (str): The boundary data file

        Returns:
            (bool): Whether the view was create or not
        """
        log.info(f"Creating a temporary table, this make take awhile...")
        if boundary:
            file = open(boundary, "r")
            data = geojson.load(file)
            aoi = shape(data["geometry"])
            file.close()
            sql = f"CREATE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{aoi.wkt}'), geom)"
            # print(sql)
        else:
            # By default, get all the highways
            sql = f"CREATE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL"
            # print(sql)
        self.curs.execute(sql)

    def filter_rows(self,
                    rows: list,
                    strip_refs: bool = True,
                    ) -> list:
        """
        Filter the rows to create a real geometry.

        Args:
            rows (list): The rows to process

        Returns:
            (list): The filtered data
        """
        features = list()
        pbar = tqdm.tqdm(rows)

        log.info(f"Filtering the query output to create real geometries")
        for row in pbar:
            osm_id = row[0]
            version = row[1]
            timestamp = row[2]
            refs = row[3]
            tags = row[4]
            geom = shapely.from_wkt(row[5])
            if strip_refs:
                data = {"osm_id": osm_id, "version": version}
            else:
                data = {"osm_id": osm_id, "version": version, "refs": refs}
            data.update(tags)
            # print(data)
            features.append(Feature(geometry=geom, properties=data))

        return features

    def execute_query(self,
                    sql: str = None,
                    ) -> list:
        """
        Execute an SQL query.

        Args:
            sql (str): The SQL to execute

        Returns:
            (list): The result of the SQL query
        """
        data = list()
        if not sql:
            log.error(f"Need to specify an SQL query!")

        self.curs.execute(sql)

        return self.curs.fetchall()

def main():
    """
    This program queries a postgres database as maintained by Underpass.
    """
    parser = argparse.ArgumentParser(description="Query a DB and output to OSM XML format")
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-b","--boundary", help='Optional boundary to clip the data')
    parser.add_argument("-o","--outfile", default='out.geojson', help='The output file')
    parser.add_argument("-u", "--uri", help="Database URI")
    parser.add_argument("-s", "--sql", help="Custom SQL Query")

    args = parser.parse_args()

    # if verbose, dump to the terminal
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )


    db = DBExtract(args.uri)
    # Make a temporary view to reduce the data size
    if args.boundary:
        db.create_view(args.boundary)
    else:
        db.create_view()

    # Query the database for what we want
    sql = f"SELECT osm_id,version,timestamp,refs,tags,ST_AsTEXT(geom) FROM highway_view WHERE tags->>'highway' IS NOT NULL;"
    rows = db.execute_query(sql)

    features = db.filter_rows(rows)

    log.debug(f"Writing data to GeoJson file, this make take awhile...")
    file = open(args.outfile, "w")
    geojson.dump(FeatureCollection(features), file, indent=2, default=str)
    file.close()
    log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
