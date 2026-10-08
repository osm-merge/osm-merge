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
import gpxpy.gpx
# Instantiate logger
log = logging.getLogger(__name__)

import osm_merge as om
rootdir = om.__path__[0]

class DistanceAddrs(DBExtract):
    def __init__(self,
                 osmuri: str,
                 routing: str,
                 ):
        """
        Initialize the database connection.

        Args:
            osmuri (str): The OSM database to use
            routing (str): The PGRoutinh database to use

        Returns:
            DistanceAddrs: An instance of this class
        """
        self.curs = None
        self.db = None
        if osmuri:
            super().__init__(osmuri)

        if routing:
            host = routing.split('/')[0]
            db = routing.split('/')[1]
            try:
                pargs = f"dbname={db}"
                if host != "localhost":
                    pargs+= f" host={host}"
                self.pgrdb = psycopg2.connect(pargs)
                self.pgrcurs = self.pgrdb.cursor()
                log.info(f"Connected to database {db} on {host}")
            except Exception as e:
                log.error(f"Couldn't connect to database: {e}")
        # self.pgr = PGRouting(dbname='gilpin_routing', user='rob')
        # if self.pgr._conn   is None:
        #     log.error(f"Failed to connect to {routing} database")
        # else:
        #     log.info(f"Connected to {routing} database")

        # self.pgr.set_meta_data(cost='cost_s', reverse_cost='reverse_cost_s', directed=True)

    def find_nearest_point(self,
                     node: str,
                     ) -> dict:
        """
        Query the PGRouting table to find the nearest node, which
        we assume is the driveway nearest the house. This table is
        only the intersections of highways, so the found node won't
        be something else.

        Args:
            node (str): A geometry in WKT format.

        Returns:
            (dict): The nearest node
        """
        sql = f"SELECT osm_id,ST_AsText(geom),geom <-> ST_GeogFromText(\'SRID=4326;{node}\') AS distance FROM ways_vertices_pgr ORDER BY distance LIMIT 1;"
        self.pgrcurs.execute(sql)
        result = self.pgrcurs.fetchall()

        return result[0]

    def find_nearest_highway(self,
                     node: str,
                     ) -> dict:
        """
        Query the OSM database to find the nodes in a highway.

        Args:
            node (str): A geometry in WKT format.

        Returns:
            (dict): The nearest node on the highway.
        """
        sql = f"SELECT osm_id,tags,ST_AsText(geom),geom <-> ST_GeogFromText(\'SRID=4326;{node}\') AS distance FROM highway_view WHERE tags->>'highway'='primary' ORDER BY distance LIMIT 1"
        # print(f"ROUTE: {sql}")
        nearest = self.execute_query(sql)

        sql = f"SELECT * FROM ways WHERE osm_id='{nearest[0][0]}'"
        self.pgrcurs.execute(sql)
        pgr = self.pgrcurs.fetchall()

        return pgr

    def make_route(self,
                   source: dict,
                   target: dict,
                   ) -> list:
        """
        """
        route = list()
        sql = f"SELECT * FROM pgr_dijkstra('SELECT id, source, target, cost, reverse_cost FROM ways',{source}, {target},directed := true);"
        self.pgrcurs.execute(sql)
        route = self.pgrcurs.fetchall()

        return route

    def get_addrs(self,
                  street: str,
                  ) -> list:
        """
        Get all the addresses in the boundary.

        Args:
            street (str): The street name from OSM

        Returns:
            (list): All the addresses on this street
        """
        addrs = list()
        sql = f"SELECT tags->>'addr:housenumber', ST_AsText(geom) AS geom FROM address_view WHERE tags->>'addr:street' LIKE '{street}';"
        result = self.execute_query(sql, "address_view")
        if len(result) > 0:
            number = result[0][0]
            geom = result[0][1]
            # file.write(f"{name},{count}\n")
            log.debug(f"{street} has {len(result)} addresses")
            addrs.append({"street": street, "number": number, "geom": geom})

        if len(result) > 0:
            number = result[0][0]
            addrs.append({"street": street, "number": number, "geom": geom})

        return addrs

    def route_addr(self,
                   source: long,
                   target: long,
                   ):
        """
        Route an address to the nearest decent highway.
        """
        sql = "SELECT * FROM pgr_dijkstra('SELECT * FROM ways', {source}, {target}, directed := true);"
        result = db.execute_query(sql)
        if len(result) > 0:
            count = result[0][0]
            node_addrs[name] = count
            # file.write(f"{name},{count}\n")
            log.debug(f"{name} has {count} addresses")

def main():
    """
    This program queries a postgres database as maintained by Underpass.
    """
    parser = argparse.ArgumentParser(description="Calculate distance to the nearest decent highway")
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-b","--boundary", help='Optional boundary to clip the data')
    parser.add_argument("-o","--outfile", default='out.csv', help='The output file')
    parser.add_argument("-u", "--osmuri", help="OSM Database URI")
    parser.add_argument("-r", "--routedb", help="PGRouting Database URI")

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

    db = DistanceAddrs(args.osmuri, args.routedb)

    # Make a temporary view to reduce the data size
    if args.boundary:
        db.create_highway_view(args.boundary)
        db.create_address_view(args.boundary)
    else:
        db.create_highway_view()
        db.create_address_view()

    highway_views = db.list_views("highway")
    # print(highway_views)

    addr_views = db.list_views("address")
    # print(addr_views)
    if len(highway_views) == 0 and len(addr_views) == 0:
        log.error(f"No data in the database views!")

    # Query the database for what we want
    sql = f"SELECT osm_id,version,timestamp,refs,tags,ST_AsTEXT(geom) FROM "
    rows = db.execute_query(sql)
    if len(rows) == 0:
        log.error(f"No data returned from the query!")
        return
    highset = set()
    for highway in rows:
        tags = highway[4]
        # FIXME: only needed for non OSM data
        if "name" in tags:
            #     new = ca.convert(tags["name"])
            highset.add(tags["name"])

    # Use GPX instead of GeoJson so we can specify the line color
    for name in sorted(highset):
        # Embedded single quotes are evil
        name = name.replace("'", "\"")
        addrs = db.get_addrs(name)
        if len(addrs) == 0:
            log.warning(f"No addresses found on {name}")
            continue
        for addr in addrs:
            gpx = gpxpy.gpx.GPX()
            gpx.nsmap["osm_merge"] = "https://osmmerge.org"
            gpx.creator = "distance_addrs 0.1"
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            outfile = f"{addr["number"]}_{addr["street"]}.gpx"
            vertic = db.find_nearest_point(addr["geom"])
            way = db.find_nearest_highway(vertic[1])
            node = db.find_nearest_highway(addr["geom"])
            if len(way) == 0:
                log.error(f"No suitable highways were found near {node}")
            if len(node) == 0 or len(way) == 0:
                continue
            source = node[0][0]
            target = way[len(way) - 1][0]
            route = db.make_route(source, target)
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            for segment in route:
                # FIXME: the coords are also in the route, the first one is missing one
                # of the coordinates.
                sql = f"SELECT x, y FROM ways_vertices_pgr WHERE id='{segment[0]}';"
                db.pgrcurs.execute(sql)
                coords = db.pgrcurs.fetchall()
                lat = coords[0][1]
                lon = coords[0][0]
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))
            # print(f"VERTIC: {vertic}")
            # print(f"ADDR: {addr}")
            # print(f"NODE: {node}")
            # print(f"WAY: {way[0]}")
            gpxfile = open(outfile, "w")
            gpxfile.write(gpx.to_xml())
    # sql = "SELECT *"
    # db.execute_query(sql)
    # path = Path(args.outfile)
    # if path.suffix == ".geojson":
    #     log.debug(f"Writing data to GeoJson file, this make take awhile...")
    #     file = open(args.outfile, "w")
    #     geojson.dump(FeatureCollection(features), file, indent=2, default=str)
    #     file.close()
    #     log.info(f"Wrote {args.outfile}")address

if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
