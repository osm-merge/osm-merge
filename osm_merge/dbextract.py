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
from geojson import Point, Feature, FeatureCollection, LineString
from shapely.geometry import LineString, shape
import shapely
import psycopg2
from osm_merge.osmfile import OsmFile


# Instantiate logger
log = logging.getLogger(__name__)

import osm_merge as om
rootdir = om.__path__[0]


def main():
    """
    This program queries a postgres database as maintained by Underpass.
    """
    parser = argparse.ArgumentParser(description="Convert ODK XML instance file to OSM XML format")
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-b","--boundary", help='Optional boundary to clip the data')
    parser.add_argument("-o","--outfile", default='out.geojson', help='The output file')
    parser.add_argument("-u", "--uri", default='localhost/underpass', help="Database URI")

    args = parser.parse_args()

    # if verbose, dump to the terminal
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )
    try:
        uri = "dbname=underpass"
        pg = psycopg2.connect(uri)
        curs = pg.cursor()
    except Exception as e:
        log.error(f"Couldn't connect to database: {e}")


    # Make a temporary view to reduce the data size
    if args.boundary:
        # optionally clip by a boundary
        file = open(args.boundary, "r")
        data = geojson.load(file)
        aoi = shape(data["geometry"])
        file.close()
        sql = f"CREATE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{aoi.wkt}'), geom)"
        # print(sql)
        curs.execute(sql)
    else:
        # By default, get all the highways
        sql = f"CREATE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL"
        # print(sql)
        curs.execute(sql)

    sql = f"SELECT osm_id,version,timestamp,refs,tags,ST_AsTEXT(geom) FROM highway_view WHERE tags->>'highway' IS NOT NULL;"
    # print(sql)
    curs.execute(sql)
    result = curs.fetchall()
    features = list()
    for row in result:
        osm_id = row[0]
        version = row[1]
        # timestamp = row[2]
        refs = row[3]
        tags = row[4]
        geom = shapely.from_wkt(row[5])
        data = {"osm_id": osm_id, "version": version, "refs": refs, "geom": geom}
        data.update(tags)
        # print(data)
        features.append(Feature(geometry=geom, properties=data))

    path = Path(args.outfile)

    if path.suffix == '.geojson':
        file = open(args.outfile, "w")
        geojson.dump(FeatureCollection(features), file)
        file.close()
    elif path.suffix == '.osm':
        osm = OsmFile()
        osm.writeOSM(features, "foo.osm")

    log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
#    loop = asyncio.new_event_loop()
#    asyncio.set_event_loop(loop)
 #   loop.run_until_complete(main())
