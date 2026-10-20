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
from shapely.geometry import LineString, shape, Polygon, Point, MultiLineString, MultiPolygon
from shapely import ops
from shapely.ops import unary_union

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
import shapely.wkt
import pyproj
import osm_merge as om
rootdir = om.__path__[0]
import math
from shapely import buffer


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
                self.pgrdb.autocommit = True
            except Exception as e:
                log.error(f"Couldn't connect to database: {e}")
        # self.pgr = PGRouting(dbname='gilpin_routing', user='rob')
        # if self.pgr._conn   is None:
        #     log.error(f"Failed to connect to {routing} database")
        # else:
        #     log.info(f"Connected to {routing} database")

        # self.pgr.set_meta_data(cost='cost_s', reverse_cost='reverse_cost_s', directed=True)
        self.sources = list()
        self.targets = list()
        self.highways = dict()

    def find_nearest_vertex(self,
                          node: Point,
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
        poly = self.make_boundary(node)
        sql = f"CREATE OR REPLACE TEMP VIEW pg_view AS SELECT * FROM ways_vertices_pgr WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{poly.wkt}'), geom)"
        # print(sql)
        self.pgrcurs.execute(sql)

        threshold = 1000 # in meters
        sql = f"SELECT row_to_json(pg_view) as row FROM pg_view WHERE ST_Distance(geom, ST_GeomFromEWKT('SRID=4326;{node.wkt}')::geography) < {threshold} ORDER BY ST_Distance(geom, ST_GeomFromEWKT('SRID=4326;{node.wkt}')) LIMIT 1;"

        self.pgrcurs.execute(sql)
        result = self.pgrcurs.fetchall()

        if len(result) == 0:
            log.warning(f"No nearby verticies found within {threshold} meters!")
            return dict()

        return result[0][0]

    def make_buffer (self,
                     highway: LineString,
                     radius: int = 0.00001,
                     ) -> Polygon:
        """
        """
        # sql = f"SELECT ST_AsText(ST_Buffer(ST_GeomFromText('SRID=4326;{highway.wkt}::geography'), {radius}, 'join=bevel'));"
        # self.pgrcurs.execute(sql)
        # result = self.pgrcurs.fetchall()
        # poly =  shapely.wkt.loads(result[0][0])

        poly = buffer(highway, radius)

        return poly

    def make_boundary(self,
                     node: Point,
                     radius: int = 100,
                     ) -> Polygon:
        """
        """
        sql = f"SELECT ST_AsText(ST_Buffer(ST_GeomFromText('{node.wkt}'), {radius}));"
        self.pgrcurs.execute(sql)
        result = self.pgrcurs.fetchall()
        poly =  shapely.wkt.loads(result[0][0])
        return poly

    def find_major_highways(self,
                        ) -> dict:
        """
        Extract all major highways.

        """
        highways = dict()
        # sql = f"SELECT osm_id,tags,ST_AsText(geom) FROM highway_view WHERE tags->>'highway'='primary' OR tags->>'highway'='tertiary' OR tags->>'highway'='secondary'"
        sql = f"SELECT osm_id,tags,ST_AsText(geom) FROM highway_view WHERE tags->>'highway'='primary' OR tags->>'highway'='secondary'"
        print(f"ROUTE: {sql}")
        major = self.execute_query(sql)

        tags = ["osm_id", "tags", "geom", "distance"]
        # Combine all the LineStrings
        for entry in major:
            highway = dict(zip(tags, entry))
            key = str()
            if "name" not in highway["tags"]:
                name = "unknown"
            elif "name" in highway["tags"]:
                name = highway["tags"]["name"]
            elif "ref" in highway["tags"]:
                name = highway["tags"]["ref"]

            if name not in highways:
                highways[name] = dict()
                highways[name]["lines"] = list()
                highways[name]["tags"] = highway["tags"]

            highways[name]["lines"].append(highway["geom"])
        for name, segments in highways.items():
            multi = list()
            for line in segments["lines"]:
                multi.append(shapely.wkt.loads(line))
            all = MultiLineString(multi)
            highline = ops.linemerge(all)
            highways[name]["buffer"] = self.make_buffer(highline)
            verts = self.get_vertics(name)

        return highways

    def get_targets(self,
                    node: Point,
                    highways: MultiPolygon,
                    threshold: float = 10.0,
                    ) -> list:
        """
        """
        targets = list()
        # sql = f"SELECT id,ST_DISTANCE(ST_GeomFromEWKT('SRID=4326;POINT (-105.4970686 39.917249)'), geom) AS distance FROM ways_vertices_pgr WHERE ST_DISTANCE(ST_GeomFromEWKT('SRID=4326;{node.wkt}'), geom) < {threshold} ORDER BY distance;"
        sql = f"SELECT id,ST_DISTANCE(ST_GeomFromEWKT('SRID=4326;{node.wkt}'), geom::geography) AS distance FROM ways_vertices_pgr WHERE ST_Contains(ST_GeomFromEWKT('SRID=4326;{highways.wkt}'), geom) ORDER BY distance LIMIT 10;"
        # sql = f"SELECT id,ST_DISTANCE(ST_GeomFromEWKT('SRID=4326;{highways.wkt}'), geom) AS distance FROM ways_vertices_pgr WHERE ST_Contains(ST_GeomFromEWKT('SRID=4326;{highways.wkt}'), geom) ORDER BY distance;"
        # print(sql)
        self.pgrcurs.execute(sql)

        result = self.pgrcurs.fetchall()
        vertices = dict()
        for row in result:
            vertices[row[0]] = row[1]

        return vertices

    def make_route(self,
                   source: int,
                   targets: dict,
                   ) -> list:
        """
        Use PGRouting to generate a list of rouing options.

        Args:
            source (int): The ID of the target in the ways_vertices_pgr table
            targets (dict): The list of target IDs in the ways_vertices_pgr table

        Returns:
            (list): the list of possible routes to analyze
        """
        routes = list()
        nodes = list()
        for id, dist in targets.items():
            nodes.append(id)

        if len(targets) == 0:
            log.warning(f"No targets for source {source}!")
            return routes
        sql = f"SELECT res.path_seq, res.node, res.edge, ST_AsText(e.geom), res.cost, e.reverse_cost, e.reverse_cost_s FROM pgr_dijkstra('SELECT id as id, source, target, cost_s AS cost FROM ways', {source}, ARRAY{nodes}, directed := true) AS res JOIN ways e ON res.edge = e.id;"
        # sql = f"SELECT res.end_vid, res.node, e.cost_s, ST_AsText(e.geom) FROM pgr_dijkstra('SELECT id as id, source, target, length_m as cost FROM ways', {source}, {target}, directed := false) AS res JOIN ways e ON res.edge = e.id;"
        self.pgrcurs.execute(sql)
        result = self.pgrcurs.fetchall()
        # print(sql)

        tags = ["sequence", "node", "edge", "geom", "cost", "reverse_cost", "reverse_cost_s"]
        route = list()
        previous = 1
        # Multiple routes are in the result, so we have to check for the transition
        # and store them all seperately.
        for row in result:
            data = dict(zip(tags, row))
            if int(data["sequence"]) < previous:
                routes.append(route)
            if int(data["sequence"]) == 1:
                route = list()
            previous = int(data["sequence"])
            route.append(data)

        return routes

    def get_vertics(self,
                    name: str,
                    ) -> bool:
        """
        """
        sources = list()
        targets = list()
        try:
            sql = f"SELECT id, source, target, ST_AsText(geom) FROM ways WHERE name='{name}'"
            self.pgrcurs.execute(sql)
            result = self.pgrcurs.fetchall()
        except:
            breakpoint()
        for row in result:
            if name not in self.highways:
                self.highways[name] = dict()
                self.highways[name]["sources"] = list()
                self.highways[name]["targets"] = list()
            self.highways[name]["sources"].append(row[1])
            self.highways[name]["targets"].append(row[2])

        # if len(self.sources) == 0 or len(self.targets) == 0:
        #     log.error(f"No source or targets found!")
        #     return False

        return True

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
        sql = f"SELECT tags->>'addr:housenumber', ST_AsText(geom) AS geom FROM address_view WHERE tags->>'addr:street'='{street}';"
        result = self.execute_query(sql, "address_view")
        if len(result) > 0:
            for entry in result:
                number = entry[0]
                geom = entry[1]
                addrs.append({"street": street, "number": number, "geom": geom})

        return addrs

    def get_highways(self,
                    name: str,
                    ) -> list:
        """
        """
        sql = "SELECT "

    def make_track(self,
                  route: list,
                  ):
        """

        """
        # print(f"SEGMENT: {segment}")
        # multi = list()
        # for name, values in majors.items():
        #     multi.append(shapely.wkt.loads(values["buffer"]))
        # bar = MultiLineString(multi)
        # highline = ops.linemerge(bar)

        # if type(highline) == MultiLineString:
        #     log.debug(f"LINE PROBLEM: {segment}")
        #     # bar = list()
        #     # for line in highline.geoms:
        #     #     bar.append(line)
        #     # foo = ops.linemerge(bar)
        #     return None, False
        # verts = list()
        # try:
        #     for point in highline.coords:
        #         sql = f"SELECT id, osm_id FROM ways_vertices_pgr WHERE x={point[0]} AND y={point[1]}"
        #         self.pgrcurs.execute(sql)
        #         result = self.pgrcurs.fetchall()
        #         if len(result) > 0:
        #             verts.append(int(result[0][0]))
        # except:
        #     breakpoint()
        # print(f"VERTs: {verts}")

        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        for segment in route:
            source = int(segment["edge"])
            target = segment["node"]
            for name, data in self.highways.items():
                line = shapely.wkt.loads(segment["geom"])
                start = line.coords[0]
                end = line.coords[1]
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(start[1], start[0]))
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(end[1], end[0]))
                print(f"FOO: {name} {segment} {segment["node"] in data["targets"]}")
                if segment["node"] in data["targets"]:
                    return gpx_segment, True

        return gpx_segment, True
            #segline = shapely.wkt.loads(segment["geom"])
            # try:
            #     highline = shapely.wkt.loads(highway["geom"])
            # except:
            #     breakpoint()
            # print(f"LEN: {highway.length}")
        # geom = shapely.wkt.loads(segment[4])
        # print(f"FIXME:  {target}: {target in verts}")
        # print(f"FIXME:  {target}: {highline.touches(segline)}")
        # print(f"FIXME1: {target}: {segline.intersects(highline)}")
        # print(f"FIXME2: {target}: {segline.within(highline)}")

        sql = f"SELECT name, osm_id, source, target, length, x1,y1,x2,y2, cost, cost_s FROM ways WHERE target='{target}' AND source!='{source}'"
        self.pgrcurs.execute(sql)
        result = self.pgrcurs.fetchall()
        tags = ["name", "osm_id", "source", "target", "length", "x1", "y1", "x2", "y2", "cost", "cost_s"]
        if len(result) != 0:
            data = dict(zip(tags, result[0]))
        else:
            data = dict(zip(tags, [0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        done = False
        print(f"DATA: {data}")
        if int(segment["node"]) == 5107:
            breakpoint()
            pass

        # if target in verts and segline.intersects(highline) and segline.within(highline):
        #     done = True
        #     log.debug(f"Last segment! {segment}")
        # for node in segline.coords:
        #     pt = Point(node[0], node[1])
        #     pt1 = Point(data["x1"], data["y1"])
        #     pt2 = Point(data["x2"], data["y2"])
        #     print(f"PT: {pt.equals(pt2)}")
        #     touch = highline.touches(pt)
        #     if touch:
        #         print(f"NODE: {pt} {touch}")
        #         break
        #     if math.isclose(data["x1"], node[0]) and math.isclose(data["y1"], node[1]):
        #         print(f"CLOSE: {node} {data}")
        #         done = True
        #         break
        #     gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(node[1], node[0]))
        #     if target in verts and done:
        #         log.debug(f"Last segment! {segment}")
        #         break
        return gpx_segment, done

def main():
    """
    This program queries a postgres database as to plot potenial emergency egress routes.
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

    # colors = {"route1": "#ff5020", "route2": "#ff5020", "route 3": "#a71de1"}

    # Use GPX instead of GeoJson so we can specify the line color
    major = db.find_major_highways()
    polys = list()
    for name, values in major.items():
        polys.append(values["buffer"])
        db.get_vertics(name)
    aoi = unary_union(polys)

    for name in sorted(highset):
        # Embedded single quotes are evil
        name = name.replace("'", "\"")
        addrs = db.get_addrs(name)
        if len(addrs) == 0:
            log.warning(f"No addresses found on {name}")
            continue
        else:
            log.debug(f"Found {len(addrs)} addresses for {name}")
        for addr in addrs:
            # if addr["number"] == '1303':
            #     breakpoint()
            gpx = gpxpy.gpx.GPX()
            gpx.nsmap["osm_merge"] = "https://osmmerge.org"
            # color = etree.Element("{osmand}color", nsmap=gpx.nsmap)
            # color.text = colors[icon]
            gpx.creator = "distance_addrs 0.1"
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            print(f"ADDR: {addr}")
            node = shapely.wkt.loads(addr["geom"])
            print(f"NODE: {node.y}, {node.x}")
            nearest = db.find_nearest_vertex(node)
            # print(f"NEAREST: {nearest}")
            # highway = db.find_nearest_highway(nearest)
            # print(f"HIGHWAY: {highway}")
            # if node is None or len(highway) == 0:
            #     log.warning(f"No suitable highways were found near {node}")
            #     continue
            pt = shape(nearest["geom"])
            targets = db.get_targets(pt, aoi)

            # print(f"TARGETS: {targets}")
            if targets == 0:
                log.warning(f"No targets found for {highway}")
                continue
            routes = db.make_route(nearest["id"], targets)
            log.debug(f"There are {len(routes)} routes in the result.")
            length = 0
            for route in routes:
                #for segment in route:
                part, done = db.make_track(route)
                gpx_track.segments.append(part)
                #     if done:
                #         break
                # if done:
                #     break
            outfile = f"{addr["number"]}_{addr["street"].replace(" ", "_")}.gpx"
            # gpx_track.desc = f"Length {length} meters"
            # gpx_track.description = f"Length {gpx_track.length_2d()} meters"
            # gpx_track.description = f"Length {gpx_track.length_2d()} meters or {gpx_track.length_2d() / 0.3048} feet"
            with open(outfile, "w") as gpxfile:
                gpxfile.write(gpx.to_xml())
            log.debug(f"Wrote {outfile}")

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
