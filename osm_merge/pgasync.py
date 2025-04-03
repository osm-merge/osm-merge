#!/usr/bin/python3

# Copyright (c) 2024, 2025 OpenStreetMap US
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import geojson
import requests
from geojson import Feature, FeatureCollection, Polygon
from shapely import wkt
from shapely.geometry import Polygon, shape

# Find the other files for this project
import osm_rawdata as rw
from osm_rawdata.config import QueryConfig

rootdir = rw.__path__[0]

# Instantiate logger
log = logging.getLogger(__name__)


class DatabaseAccess(object):
    def __init__(self):
        """This is a class to setup a database connection."""
        self.pg = None
        self.dburi = None
        self.qc = None
        self.clipped = False

    async def connect(
        self,
        dburi: str,
    ):
        self.dburi = dict()
        uri = urlparse(dburi)
        if not uri.username:
            self.dburi["dbuser"] = os.getenv("PGUSER", default=None)
            if not self.dburi["dbuser"]:
                log.error(
                    "You must specify the user name in the database URI, or set PGUSER"
                )
        else:
            self.dburi["dbuser"] = uri.username
        if not uri.password:
            self.dburi["dbpass"] = os.getenv("PGPASSWORD", default=None)
            if not self.dburi["dbpass"]:
                log.error(
                    "You must specify the user password in the database URI, or set PGPASSWORD"
                )
        else:
            self.dburi["dbpass"] = uri.password
        if not uri.hostname:
            self.dburi["dbhost"] = os.getenv("PGHOST", default="localhost")
        else:
            self.dburi["dbhost"] = uri.hostname

        slash = uri.path.find("/")
        self.dburi["dbname"] = uri.path[slash + 1 :]
        connect = f"postgres://{self.dburi['dbuser']}:{self.dburi['dbpass']}@{self.dburi['dbhost']}/{self.dburi['dbname']}"

        if self.dburi["dbname"] == "underpass":
            # Authentication data
            # self.auth = HTTPBasicAuth(self.user, self.passwd)

            # Use a persistant connect, better for multiple requests
            self.session = requests.Session()
            self.url = os.getenv(
                "RAW_DATA_API_URL", "https://raw-data-api0.hotosm.org/v1"
            )
            self.headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }
        else:
            # log.debug(f"Connecting with: {connect}")
            try:
                self.pg = await asyncpg.connect(connect)
                if self.pg.is_closed():
                    log.error(f"Couldn't open cursor in {self.uri['dbname']}")
                else:
                    log.info(f"Connected to database {dburi}")
            except Exception as e:
                log.error(f"Couldn't connect to database: {e}")

    async def createJson(
        self,
        config: QueryConfig,
        boundary: Polygon,
        allgeom: bool = False,
    ):
        """This class generates a JSON file, which is used for remote access
        to an OSM raw database using the Underpass schema.

        Args:
            config (QueryConfig): The config data from the query config file
            boundary (Polygon): The boundary polygon
            allgeom (bool): Whether to return centroids or all the full geometry

        Returns:
            (FeatureCollection): the json data
        """
        feature = dict()
        feature["geometry"] = boundary

        filters = dict()
        filters["tags"] = dict()
        # filters["tags"]["all_geometry"] = dict()

        # This only effects the output file
        geometrytype = list()
        # for table in config.config['tables']:
        if (
            len(config.config["select"]["nodes"]) > 0
            or len(config.config["where"]["nodes"]) > 0
        ):
            geometrytype.append("point")
        if (
            len(config.config["select"]["ways_line"]) > 0
            or len(config.config["where"]["ways_line"]) > 0
        ):
            geometrytype.append("line")
        if (
            len(config.config["select"]["ways_poly"]) > 0
            or len(config.config["where"]["ways_poly"]) > 0
        ):
            geometrytype.append("polygon")
        feature["geometryType"] = geometrytype

        tables = {"nodes": "point", "ways_poly": "polygon", "ways_line": "line"}
        # The database tables to query
        # if tags exists, then only query those fields
        join_or = {
            "point": [],
            "polygon": [],
            "line": [],
        }
        join_and = {
            "point": [],
            "polygon": [],
            "line": [],
        }
        filters["tags"] = {
            "point": {"join_or": {}, "join_and": {}},
            "polygon": {"join_or": {}, "join_and": {}},
            "line": {"join_or": {}, "join_and": {}},
        }
        for table in config.config["where"].keys():
            for item in config.config["where"][table]:
                key = list(item.keys())[0]
                if item["op"] == "or":
                    join_or[tables[table]].append(key)
                if item["op"] == "and":
                    join_and[tables[table]].append(key)
                if "not null" in item.get(key, []):
                    filters["tags"][tables[table]]["join_or"][key] = []
                    filters["tags"][tables[table]]["join_and"][key] = []
                else:
                    filters["tags"][tables[table]]["join_or"][key] = item[key]
                    filters["tags"][tables[table]]["join_and"][key] = item[key]
        feature.update({"filters": filters})

        attributes = list()
        for table, data in config.config["select"].items():
            for value in data:
                [[k, v]] = value.items()
                if k not in attributes:
                    attributes.append(k)

        # Whether to dump centroids or polygons
        if "centroid" in config.config:
            feature["centroid"] = true
        return json.dumps(feature)

    async def recordsToFeatures(
        self,
        records: list,
    ) -> list:
        """Convert an asyncpg.Record to a GeoJson FeatureCollection.

        Args:
            records (list): The records from an SQL query

        Returns:
            (list): The converted data
        """
        data = list()
        keys = self.qc.getKeys()
        for entry in records:
            i = 0
            geom = None
            last = len(entry) - 1
            props = dict()
            while i <= last:
                if keys[i] == "geometry":
                    geom = wkt.loads(entry[i])
                elif entry[i] is not None:
                    props[keys[i]] = entry[i]
                i += 1
            data.append(Feature(geometry=geom, properties=props))

        return data

    async def createSQL(
        self,
        config: QueryConfig,
        allgeom: bool = True,
    ):
        """This class generates the SQL to query a local postgres database.

        Args:
            config (QueryConfig): The config data from the query config file
            allgeom (bool): Whether to return centroids or all the full geometry

        Returns:
            (FeatureCollection): the json
        """
        sql = list()
        query = ""
        for table in config.config["tables"]:
            select = "SELECT "
            if allgeom:
                select += "ST_AsText(geom) AS geometry"
            else:
                select += "ST_AsText(ST_Centroid(geom)) AS geometry"
            # FIXME: This part is OSM specific, and should be made more
            # general. these two columns are OSM attributes, so each
            # have their own column in the database. All the other
            # values are in a single JSON column.
            select += ", osm_id, version, "
            for entry in config.config["select"][table]:
                for k1, v1 in entry.items():
                    if k1 == "osm_id" or k1 == "version":
                        continue
                    select += f"tags->>'{k1}', "
            select = select[:-2]

            join_or = list()
            join_and = list()
            for entry in config.config["where"][table]:
                # print(entry)
                if "op" not in entry:
                    pass
                op = entry["op"]
                for k, v in entry.items():
                    if k == "op":
                        continue
                    if op == "or":
                        # print(f"1: {k}=\'{v}\' OR ")
                        join_or.append(entry)
                    elif op == "and":
                        # print(f"2: {k}=\'{v}\' AND ")
                        join_and.append(entry)
            # jor = '('
            jor = ""
            for entry in join_or:
                for k, v in entry.items():
                    if type(v[0]) == list:
                        # It's an array of values
                        value = str(v[0])
                        any = f"ANY(ARRAY{value})"
                        jor += f"tags->>'{k}'={any} OR "
                        continue
                    if k == "op":
                        continue
                    if len(v) == 1:
                        if v[0] == "not null":
                            v1 = "IS NOT NULL"
                        else:
                            v1 = f"='{v[0]}'"
                    elif len(v) > 0:
                        v1 = f" IN {str(tuple(v))}"
                    else:
                        v1 = "IS NOT NULL"
                    jor += f"tags->>'{k}' {v1} OR "
            # print(f"JOR: {jor}")

            jand = ""
            for entry in join_and:
                for k, v in entry.items():
                    if k == "op":
                        continue
                    if len(v) == 1:
                        if v[0] == "not null":
                            v1 = "IS NOT NULL"
                        else:
                            v1 = f"='{v[0]}'"
                    elif len(v) > 0:
                        v1 = f" IN {str(tuple(v))}"
                    else:
                        v1 = "IS NOT NULL AND"
                    jand += f"tags->>'{k}' {v1} AND "
            # print(f"JAND: {jand}")
            query = f"{select} FROM {table} WHERE {jor} {jand}".rstrip()
            # if query[len(query)-5:] == ' OR  ':
            # print(query[:query.rfind(' ')])
            sql.append(query[: query.rfind(" ")])

        return sql

    async def createTable(
        self,
        sql: str,
    ):
        """Create a table in the database

        Args:
            sqlfile (str): The SQL

        Returns:
            (bool): The table creation status
        """
        log.info("Creating table schema")
        result = await self.execute(sql)

        path = Path(sqlfile)
        sql = f"INSERT INTO schemas(schema, version) VALUES('{sqlfile.stem}', 1.0)"
        result = self.pg.execute(sql)

        return True

    async def getRecordCount(
        self,
        table: str,
        column: str = "id",
    ):
        # FIXME: we should cleanup this mess between US and British spelling
        if table == "organizations":
            newtable = "organisations"
        else:
            newtable = table
        sql = f"SELECT reltuples::bigint AS count FROM  pg_class WHERE relname='{newtable}';"
        result = await self.execute(sql)
        count = 0
        if len(result) == 0:
            sql = f"SELECT COUNT({column}) AS count FROM {newtable};"
            # print(sql)
            result = await self.execute(sql)
        else:
            count = result[0].get("count")

        log.debug(f"There are {count} records in {table}")
        return count

    async def getPage(
        self,
        chunk: int,
        table: str,
    ):
        """Return a page of data.

        Args:
            start (int): The ID of the first record
            end (int): The ID of the last record

        Returns:
            (list): The results of the query
        """
        result = list()
        async with self.pg.transaction():
            cur = await self.pg.cursor(f"SELECT * FROM {table}")
            result = await cur.fetch(chunk)
            await cur.forward(chunk)
            # FIXME: the hard way
            # sql = f"DECLARE c CURSOR WITH HOLD FOR SELECT row_to_json({table}) AS row FROM {table} WHERE id BETWEEN {start} AND {end} ORDER BY id; COMMIT"
        # sql = f"START TRANSACTION;DECLARE c CURSOR WITH HOLD FOR SELECT row_to_json({table}) AS row FROM {table} WHERE id BETWEEN {start} AND {end} ORDER BY id; COMMIT"
        # result = await self.pg.execute(sql)
        # sql = f"FETCH {end} FROM c;"
        # sql = f"FETCH {end} FROM c; CLOSE c"
        # result = await self.pg.execute(sql)
        # result = await self.pg.fetch(sql)
        # sql = f"MOVE ABSOLUTE {start} in c;

        return result

    async def execute(
        self,
        sql: str,
    ) -> list:
        """Execute a raw SQL query and return the results.

        Args:
            sql (str): The SQL to execute

        Returns:
            (list): The results of the query
        """
        # print(sql)
        data = list()
        if sql.find(";") <= 0:
            queries = [sql]

        async with self.pg.transaction():
            queries = list()
            # If using an SRID, we have to hide the sem-colon so the string
            # doesn't split in the wrong place.
            cmds = sql.replace("SRID=4326;P", "SRID=4326@P").split(";")
            for sub in cmds:
                queries.append(sub.replace("@", ";"))
                continue

            for query in queries:
                try:
                    # print(query)
                    result = await self.pg.fetch(query)
                    if len(result) > 0:
                        data += result

                except Exception as e:
                    log.error(f"Couldn't execute query! {e}\n{query}")
                    return list()

        return data

    async def queryLocal(
        self,
        query: str,
        allgeom: bool = True,
        boundary: Polygon = None,
    ):
        """This query a local postgres database.

        Args:
            query (str): The SQL query to execute
            allgeom (bool): Whether to return centroids or all the full geometry
            boundary (Polygon): The boundary polygon

        Returns:
                query (FeatureCollection): the results of the query
        """
        features = list()
        # if no boundary, it's already been setup
        # if boundary and not self.clipped:
        if boundary:
            sql = f"DROP VIEW IF EXISTS ways_view;CREATE VIEW ways_view AS SELECT * FROM ways_poly WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{boundary.wkt}'), geom)"
            await self.pg.execute(sql)
            sql = f"DROP VIEW IF EXISTS nodes_view;CREATE VIEW nodes_view AS SELECT * FROM nodes WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{boundary.wkt}'), geom)"
            await self.pg.execute(sql)
            sql = f"DROP VIEW IF EXISTS lines_view;CREATE VIEW lines_view AS SELECT * FROM ways_line WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{boundary.wkt}'), geom)"
            await self.pg.execute(sql)
            sql = f"DROP VIEW IF EXISTS relations_view;CREATE VIEW relations_view AS SELECT * FROM nodes WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{boundary.wkt}'), geom)"
            await self.pg.execute(sql)

            if query.find(" ways_poly ") > 0:
                query = query.replace("ways_poly", "ways_view")
            elif query.find(" ways_line ") > 0:
                query = query.replace("ways_line", "lines_view")
            elif query.find(" nodes ") > 0:
                query = query.replace("nodes", "nodes_view")
            elif query.find(" relations ") > 0:
                query = query.replace("relations", "relations_view")

        # log.debug(query)
        result = await self.execute(query)
        # log.debug("SQL Query returned %d records" % len(result))
        # return FeatureCollection(features)

        # If there is no config file, don't modify the results
        if self.qc:
            if (
                len(self.qc.config["where"]["ways_poly"]) == 0
                and len(self.qc.config["where"]["nodes"]) == 0
            ):
                return result

        for item in result:
            if len(item) <= 1 and len(result) == 1:
                return result
                # break
            geom = wkt.loads(item[0])
            tags = dict()
            tags["id"] = item[1]
            tags["version"] = item[2]
            i = 3
            # If there are no tables, we're using a custom SQL query
            if len(self.qc.config["tables"]) > 0:
                # map the value in the select to the values returns for them.
                for _table, values in self.qc.config["select"].items():
                    for entry in values:
                        if i == len(item):
                            break
                        [[k, v]] = entry.items()
                        if item[i] is not None:
                            tags[k] = item[i]
                        i += 1
            else:
                # Figure out the tags from the custom SELECT
                end = query.find("FROM")
                res = query[:end].split(" ")
                # This should be the geometry
                geom = wkt.loads(item[0])
                # This should be the OSM ID
                tags[res[2][:-1]] = item[1]
                # This should be the version
                tags[res[3][:-1]] = item[2]
            features.append(Feature(geometry=geom, properties=tags))

        return FeatureCollection(features)
        # return features

    async def queryRemote(
        self,
        query: str = None,
    ):
        """This queries a remote postgres database using the FastAPI
        backend to the HOT Export Tool.

        Args:
            query (str): The JSON query to execute

        Returns:
            (FeatureCollection): the results of the query
        """
        url = f"{self.url}/snapshot/"
        result = self.session.post(url, data=query, headers=self.headers)
        if result.status_code != 200:
            log.error(f"{result.json()['detail'][0]['msg']}")
            return None
        task_id = result.json()["task_id"]
        newurl = f"{self.url}/tasks/status/{task_id}"
        while True:
            result = self.session.get(newurl, headers=self.headers)
            if result.json()["status"] == "PENDING":
                log.debug("Retrying...")
                time.sleep(1)
            elif result.json()["status"] == "SUCCESS":
                break
        zip = result.json()["result"]["download_url"]
        result = self.session.get(zip, headers=self.headers)
        fp = BytesIO(result.content)
        zfp = zipfile.ZipFile(fp, "r")
        zfp.extract("RawExport.geojson", "/tmp/")
        # Now take that taskid and hit /tasks/status url with get
        data = zfp.read("RawExport.geojson")
        os.remove("/tmp/RawExport.geojson")
        return json.loads(data)

    #   return zfp.read("RawExport.geojson")


class PostgresClient(DatabaseAccess):
    """Class to handle SQL queries for the categories."""

    def __init__(
        self,
        # output: str = None
    ):
        """This is a client for a postgres database.

        Returns:
            (PostgresClient): An instance of this class
        """
        super().__init__()
        self.qc = None

    async def loadConfig(
        self,
        config: str,
    ):
        """Load the JSON or YAML config file that defines the SQL query

        Args:
            config (str): The filespec for the query config file

        Returns:
            (bool): Whether the data base connection was sucessful
        """
        self.qc = QueryConfig()
        if config:
            # Load the config file for the SQL query
            path = Path(config)
            if path.suffix == ".json":
                self.qc.parseJson(config)
            elif path.suffix == ".yaml":
                self.qc.parseYaml(config)
            else:
                log.error(f"{path} is an unsupported file format!")
                quit()

    async def createDB(self, dburi: str):
        """Setup the postgres database connection.

        Args:
            dburi (str): The URI string for the database connection

        Returns:
            status (bool): Whether the data base connection was sucessful
        """
        sql = f"CREATE DATABASE IF NOT EXISTS {self.dbname}"
        result = await self.execute(sql)
        log.info("Query returned %d records" % len(result))
        # result = subprocess.call("createdb", uri.dbname)

        # Add the extensions needed
        sql = "CREATE EXTENSION postgis; CREATE EXTENSION hstore;"
        result = await self.execute(sql)
        log.info("Query returned %d records" % len(result))
        return True

    async def execQuery(
        self,
        boundary: FeatureCollection,
        customsql: str = None,
        allgeom: bool = True,
    ):
        """This class generates executes the query using a local postgres
        database, or a remote one that uses the Underpass schema.

        Args:
            boundary (FeatureCollection): The boundary polygon
            customsql (str): Don't create the SQL, use the one supplied
            allgeom (bool): Whether to return centroids or all the full geometry

        Returns:
                query (FeatureCollection): the json
        """
        log.info("Extracting features from Postgres...")

        polygons = list()
        if "geometry" in boundary:
            polygons.append(boundary["geometry"])

        if boundary["type"] == "MultiPolygon":
            # poly = boundary["features"][0]["geometry"]
            points = list()
            for coords in boundary["features"]["coordinates"]:
                for pt in coords:
                    for xy in pt:
                        points.append([float(xy[0]), float(xy[1])])
                poly = Polygon(points)
                polygons.append(poly)

        for poly in polygons:
            wkt = shape(poly)

            if not self.pg.is_closed():
                if not customsql:
                    sql = await self.createSQL(self.qc, allgeom)
                else:
                    sql = [customsql]
                alldata = list()
                queries = list()
                if type(sql) != list:
                    queries = sql.split(";")
                else:
                    queries = sql

                for query in queries:
                    # print(query)
                    result = await self.queryLocal(query, allgeom, wkt)
                    if len(result) > 0:
                        # Some queries don't return any data, for example
                        # when creating a VIEW.
                        alldata += await self.recordsToFeatures(result)
                collection = FeatureCollection(alldata)
            else:
                request = await self.createJson(self.qc, poly, allgeom)
                collection = await self.queryRemote(request)

        return collection


async def main():
    """This main function lets this class be run standalone by a bash script."""
    parser = argparse.ArgumentParser(
        prog="pgasync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Make data extract from OSM",
        epilog="""
This program extracts data from a local postgres database. A boundary polygon is used
to define the are to be covered in the extract. Optionally a data file can be used.

        """,
    )
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-u", "--uri", default="underpass", help="Database URI")
    parser.add_argument(
        "-b",
        "--boundary",
        required=True,
        help="Boundary polygon to limit the data size",
    )
    parser.add_argument(
        "-s", "--sql", help="Custom SQL query to execute against the database"
    )
    parser.add_argument("-a", "--all", help="All the geometry or just centroids")
    parser.add_argument(
        "-c", "--config", help="The config file for the query (json or yaml)"
    )
    parser.add_argument(
        "-o", "--outfile", default="extract.geojson", help="The output file"
    )
    args = parser.parse_args()

    # if len(argv) <= 1 or (args.sql is None and args.config is None):
    #     parser.print_help()
    #     quit()

    # if verbose, dump to the terminal.
    log_level = os.getenv("LOG_LEVEL", default="INFO")
    if args.verbose is not None:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s.%(msecs)03d [%(levelname)s] "
            "%(name)s | %(funcName)s:%(lineno)d | %(message)s"
        ),
        datefmt="%y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    if args.boundary:
        infile = open(args.boundary, "r")
        inpoly = geojson.load(infile)
        if inpoly["type"] == "MultiPolygon":
            poly = FeatureCollection(inpoly)
    else:
        log.error("A boundary file is needed!")

    if args.uri is not None:
        log.info("Using a Postgres database for the data source")
        db = DatabaseAccess()
        await db.connect(args.uri)
        # result = await db.execute("SELECT * FROM nodes LIMIT 10;")
        # print(result)
        # quit()
        # await db.connect(args.uri)
        # data = await db.pg.fetch("SELECT * FROM schemas LIMIT 10;")
        # print(data)
        if args.sql:
            pg = PostgresClient()
            await pg.connect(args.uri)
            sql = open(args.sql, "r")
            result = await pg.execQuery(poly, sql.read())
            log.info(f"Custom Query returned {len(result['features'])} records")
        else:
            pg = PostgresClient()
            await pg.connect(args.uri)
            await pg.loadConfig(args.config)
            result = await pg.execQuery(poly)
            # log.info(f"Canned Query returned {len(result['features'])} records")

        outfile = open(args.outfile, "w")
        geojson.dump(result, outfile)

        log.debug(f"Wrote {args.outfile}")


if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

# ./pgasync.py -u localhost/colorado -b /play/MapData/States/Colorado/Boundaries/NationalForest/MedicineBowNationalForest.geojson -c /usr/local/lib/python3.12/site-packages/osm_fieldwork/data_models/highways.yaml
