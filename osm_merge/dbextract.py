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
                self.db.autocommit = True
                log.info(f"Connected to database {db} on {host}")
            except Exception as e:
                log.error(f"Couldn't connect to database: {e}")

    def create_highway_view(self,
                    boundary: str = None,
                    ) -> bool:
        """
        Filter the data by a multi-polygon to reduce the size.

        Args:
            boundary (str): The boundary data file

        Returns:
            (bool): Whether the view was created or not
        """
        log.info(f"Creating temporary views of highways, this make take awhile...")
        views = self.list_views("highway")
        if len(views) > 0:
            log.debug(f"highway_view already exists")
            return True

        if boundary:
            file = open(boundary, "r")
            data = geojson.load(file)
            file.close()
            index = 0
            if "geometry" not in data:  # It's a FeatureCollection or MultiPolygon
                polys = list()
                for feature  in data["features"]:
                    feat = feature["geometry"]
                    foo = wkt.dumps(feat)
                    sql = f"CREATE OR REPLACE TEMP VIEW highway_view{index} AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{foo}'), geom)"
                    self.curs.execute(sql)
                    log.debug(f"Created temporary view highway_view{index}")
                    index += 1
            else:
                aoi = shape(data["geometry"])
                sql = f"CREATE OR REPLACE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{aoi.wkt}'), geom)"
                # print(sql)
                self.curs.execute(sql)
        else:
            # By default, get all the highways
            sql = f"CREATE OR REPLACE TEMP VIEW highway_view AS SELECT * FROM ways_line WHERE tags->>'highway' IS NOT NULL"
            # print(sql)
            self.curs.execute(sql)

    def create_address_view(self,
                    boundary: str = None,
                    ) -> bool:
        """
        Filter the data by a multi-polygon to reduce the size.

        Args:
            boundary (str): The boundary data file

        Returns:
            (bool): Whether the view was created or not
        """
        log.info(f"Creating temporary views of addresses, this make take awhile...")
        views = self.list_views("address")
        if len(views) > 0:
            log.debug(f"address_view already exists")
            return True

        if boundary:
            file = open(boundary, "r")
            data = geojson.load(file)
            file.close()
            index = 0
            if "geometry" not in data:  # It's a FeatureCollection or MultiPolygon
                polys = list()
                for feature  in data["features"]:
                    feat = feature["geometry"]
                    foo = wkt.dumps(feat)
                    sql = f"CREATE OR REPLACE TEMP VIEW tmp_view{index} AS SELECT * FROM nodes WHERE tags->>'addr:housenumber' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{foo}'), geom)"
                    self.curs.execute(sql)
                    log.debug(f"Created temporary address_view{index}")
                    index += 1
            else:
                aoi = shape(data["geometry"])
                sql = f"CREATE OR REPLACE TEMP VIEW tmp_view AS SELECT * FROM nodes WHERE tags->>'addr:housenumber' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{aoi.wkt}'), geom)"
                # print(sql)
                # Addresses may be on either a node or the building polygon
                self.curs.execute(sql)
                sql = f"CREATE OR REPLACE TEMP VIEW tmp_view2 AS SELECT * FROM ways_poly WHERE tags->>'addr:housenumber' IS NOT NULL AND ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{aoi.wkt}'), geom)"
                # print(sql)
                self.curs.execute(sql)
                sql = "CREATE OR REPLACE TEMP VIEW address_view AS SELECT tags,geom FROM tmp_view UNION ALL SELECT tags,ST_CENTROID(geom) FROM tmp_view2;"
                # print(sql)
                self.curs.execute(sql)
        else:
            sql = f"CREATE OR REPLACE TEMP VIEW tmp_view AS SELECT * FROM nodes WHERE tags->>'addr:housenumber' IS NOT NULL;"
            print(sql)
            # Addresses may be on either a node or the building polygon
            self.curs.execute(sql, ("auto-committed",))
            sql = f"CREATE OR REPLACE TEMP VIEW tmp_view2 AS SELECT * FROM ways_poly WHERE tags->>'addr:housenumber' IS NOT NULL;"
            print(sql)
            self.curs.execute(sql, ("auto-committed",))
            sql = "CREATE OR REPLACE TEMP VIEW address_view AS SELECT tags,geom FROM tmp_view UNION ALL SELECT tags,ST_CENTROID(geom) FROM tmp_view2;"
            print(sql)
            # print(sql)
            self.curs.execute(sql, ("auto-committed",))

    def filter_rows(self,
                    rows: list,
                    strip_refs: bool = False,
                    ) -> list:
        """
        Filter the rows to create a real geometry.

        Args:
            rows (list): The rows to process

        Returns:
            (list): The filtered data
        """
        log.info(f"Filtering the query output to create real geometries")
        features = list()
        pbar = tqdm.tqdm(rows)

        for row in pbar:
            osm_id = row[0]
            version = row[1]
            timestamp = row[2]
            if strip_refs:
                tags = row[3]
                geom = shapely.from_wkt(row[4])
                data = {"osm_id": osm_id, "version": version}
            else:
                refs = row[3]
                tags = row[4]
                geom = shapely.from_wkt(row[5])
                data = {"osm_id": osm_id, "version": version, "refs": refs}
            data.update(tags)
            # print(data)
            features.append(Feature(geometry=geom, properties=data))

        return features

    def execute_query(self,
                    sql: str = None,
                    view: str = "highway_view",
                    ) -> list:
        """
        Execute an SQL query.

        Args:
            sql (str): The SQL to execute
            view (str): Optional database view

        Returns:
            (list): The result of the SQL query
        """
        if not sql:
            log.error(f"Need to specify an SQL query!")

        # data = list()
        # temp_views = self.list_views(view)
        # if len(temp_views) == 0:
        #     log.error(f"There are no views!")
        #     return data

        # for dbview in temp_views:
        if sql.find("_view") > 0:
            newsql = sql
        else:
            newsql = sql + view + ';'
        # log.debug(newsql)
        self.curs.execute(newsql)
        result = self.curs.fetchall()

        return result

    def get_vertices(self,
                    ) -> dict:
        """
        Query the database to get only rhe major highways we want to route to..

        """
        primaries = list
        sql = f"SELECT row_to_json(highway_view) FROM highway_view WHERE tags->>'highway'='primary'"
        rows = self.execute_query(sql)
        if len(rows) == 0:
            log.error(f"No data returned from the query!")

        # for name in rows["name"]:
        #     sql = f"SELECT source, target, source_osm, target_osm FROM ways WHERE name LIKE '{name}%'"
        #     self.pgrcurs.execute(sql)
        #     result = self.pgrcurs.fetchall()
        #     nodes = list()
        #     for entry in result[0]:
        #         vertex = {"source": entry[0],
        #                 "target": entry[1],
        #                 "source_osm": entry[2],
        #                 "target_osm": entry[3],
        #                 }
        #         nodes.append(vertex)

        return nodes

    def list_views(self,
                   view: str,
                   ) -> list:
        """
        List all the temp views that match a pattern.

        Args:
            view (str): The views to look for
        """
        temp_views = list()
        sql = "SELECT table_schema AS schema, table_name AS view FROM information_schema.views WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY schema ASC, view ASC;"
        self.curs.execute(sql)
        views =  self.curs.fetchall()
        pat = re.compile(f"{view}.*")
        temp_views = list()
        for entry in views:
            match = re.search(pat, entry[1])
            if match:
                temp_views.append(match.string)

        # log.debug(f"There are {len(temp_views)} temporary views in the database")
        return temp_views

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


    db = DBExtract(args.uri)
    # Make a temporary view to reduce the data size
    if args.boundary:
        db.create_view(args.boundary)
    else:
        db.create_view()

    # Query the database for what we want
    if not args.sql:
        sql = f"SELECT osm_id,version,timestamp,refs,tags,ST_AsTEXT(geom) FROM "
    else:
        sql = args.sql
    rows = db.execute_query(sql)

    if len(rows) == 0:
        log.error(f"No data returned from the query!")
        quit()
    features = db.filter_rows(rows)

    path = Path(args.outfile)
    if path.suffix == ".geojson":
        log.debug(f"Writing data to GeoJson file, this make take awhile...")
        file = open(args.outfile, "w")
        geojson.dump(FeatureCollection(features), file, indent=2, default=str)
        file.close()
        log.info(f"Wrote {args.outfile}")
    elif path.suffix == ".osm":
        osm = OsmFile()
        osm.writeOSM(features, args.outfile)
        log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
