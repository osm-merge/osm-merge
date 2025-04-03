#!/usr/bin/python3

# Copyright (c) 2022, 2023, 2024, 2025 OpenStreetMap US 
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
import concurrent.futures
import logging
import subprocess
import sys
from pathlib import Path
from sys import argv

# from geoalchemy2 import shape
import geoalchemy2
import geojson
from codetiming import Timer
from cpuinfo import get_cpu_info
from pandas import DataFrame
from shapely import wkb
from shapely.geometry import shape
from sqlalchemy import MetaData, cast, column, create_engine, select, table, text
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

# Find the other files for this project
import osm_rawdata as rw
import osm_rawdata.db_models
from osm_rawdata.db_models import Base
from osm_rawdata.overture import Overture
from osm_rawdata.postgres import uriParser

rootdir = rw.__path__[0]
rootdir = "/usr/local/lib/python3.11/dist-packages/osm_rawdata/"


# Instantiate logger
log = logging.getLogger("osm-rawdata")

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info["count"]


def importThread(
    data: list,
    db: Connection,
):
    """Thread to handle importing

    Args:
        data (list): The list of tiles to download
        db (Connection): A database connection
    """
    # log.debug(f"In importThread()")
    # timer = Timer(text="importThread() took {seconds:.0f}s")
    # timer.start()
    ways = table(
        "ways_poly",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    nodes = table(
        "nodes",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    nodes = table(
        "ways_line",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    index = 0

    for feature in data:
        # log.debug(feature)
        index -= 1
        entry = dict()
        tags = feature["properties"]
        tags["building"] = "yes"
        entry["id"] = index
        ewkt = shape(feature["geometry"])
        geom = wkb.dumps(ewkt)
        type = ewkt.geom_type
        scalar = select(cast(tags, JSONB)).scalar_subquery()

        if type == "Polygon":
            sql = insert(ways).values(
                # id = entry['id'],
                geom=geom,
                tags=scalar,
            )
        elif type == "Point":
            sql = insert(nodes).values(
                # id = entry['id'],
                geom=geom,
                tags=scalar,
            )

        db.execute(sql)
        # db.commit()


def parquetThread(
    data: DataFrame,
    db: Connection,
):
    """Thread to handle importing

    Args:
        data (list): The list of tiles to download
        db (Connection): A database connection
    """
    timer = Timer(text="parquetThread() took {seconds:.0f}s")
    timer.start()
    ways = table(
        "ways_poly",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    nodes = table(
        "nodes",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    lines = table(
        "ways_line",
        column("id"),
        column("user"),
        column("geom"),
        column("tags"),
    )

    index = -1
    log.debug(f"There are {len(data)} entries in the data")
    if len(data) == 0:
        return

    overture = Overture()
    for index in data.index:
        feature = data.loc[index]
        dataset = feature["sources"][0]["dataset"]
        if dataset == "OpenStreetMap" or dataset == "Microsoft ML Buildings":
            continue
        tags = overture.parse(feature)
        geom = feature["geometry"]
        hex = wkb.loads(geom, hex=True)
        gdata = geoalchemy2.shape.from_shape(hex, srid=4326, extended=True)
        # geom_type = wkb.loads(geom).geom_type
        scalar = select(cast(tags["properties"], JSONB)).scalar_subquery()
        sql = None
        if hex.geom_type == "Polygon":
            sql = insert(ways).values(
                # osm_id = entry['osm_id'],
                geom=bytes(gdata.data),
                tags=scalar,
            )
        elif hex.geom_type == "MultiPolygon":
            gdata = geoalchemy2.shape.from_shape(
                hex.convex_hull, srid=4326, extended=True
            )
            sql = insert(ways).values(
                geom=bytes(gdata.data),
                tags=scalar,
            )
        elif hex.geom_type == "Point":
            sql = insert(nodes).values(
                # osm_id = entry['osm_id'],
                geom=bytes(gdata.data),
                tags=scalar,
            )
        elif hex.geom_type == "LineString":
            sql = insert(lines).values(
                # osm_id = entry['osm_id'],
                geom=bytes(gdata.data),
                tags=scalar,
            )
        else:
            log.error(f"geometry type {geom_type} is unsupported!")
            continue

        index -= 1
        db.execute(sql)
        # db.commit()
        # print(f"FIXME2: {entry}")
    timer.stop()


class MapImporter(object):
    def __init__(
        self,
        dburi: str,
    ):
        """This is a class to setup a local database for OSM data.

        Args:
            dburi (str): The URI string for the database connection

        Returns:
            (OsmImporter): An instance of this class
        """
        self.dburi = dburi
        self.db = None
        self.connections = list()
        for thread in range(0, cores + 1):
            engine = create_engine(f"postgresql://{self.dburi}", echo=False)
            if not database_exists(engine.url):
                create_database(engine.url)
            self.connections.append(engine.connect())
            sessionmaker(autocommit=False, autoflush=False, bind=engine)

            if thread == 0:
                meta = MetaData()
                meta.create_all(engine)

                # if dburi:
                # self.uri = uriParser(dburi)
                # engine = create_engine(f"postgresql://{self.dburi}", echo=True)
                # if not database_exists(engine.url):
                #     create_database(engine.url)
                # self.db = engine.connect()

                # Add the extension we need to process the data
                sql = text(
                    "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS hstore;CREATE EXTENSION IF NOT EXISTS dblink;"
                )
                self.connections[0].execute(sql)

                Base.metadata.create_all(bind=engine)

                sessionmaker(autocommit=False, autoflush=False, bind=engine)

            # Create indexes to improve peformance
            # sql = text("cluster ways_poly using ways_poly_geom_idx;")
            # self.db.execute(sql)
            # sql("create index on ways_poly using gin(tags)")
            # self.db.execute(sql)
            # self.db.commit()

    def importOSM(
        self,
        infile: str,
    ):
        """Import an OSM data file into a postgres database.

        Args:
            infile (str): The file to import
        Returns:
            (bool): Whether the import finished sucessfully
        """
        # osm2pgsql --create -d nigeria --extra-attributes --output=flex --style raw.lua nigeria-latest-internal.osm.pbf
        uri = uriParser(self.dburi)
        result = subprocess.run(
            [
                "osm2pgsql",
                "--create",
                "-d",
                f"{uri['dbname']}",
                "--extra-attributes",
                "--output=flex",
                "--style",
                f"{rootdir}/raw_with_ref.lua",
                f"{infile}",
            ]
        )
        result.check_returncode()

    def importParquet(
        self,
        infile: str,
    ):
        """Import an Overture parquet data file into a postgres database.

        Args:
            infile (str): The file to import

        Returns:
            (bool): Whether the import finished sucessfully
        """
        # spin = PixelSpinner(f"Processing {infile}...")
        timer = Timer(text="importParquet() took {seconds:.0f}s")
        timer.start()
        overture = Overture(infile)

        connections = list()
        for thread in range(0, cores + 1):
            engine = create_engine(f"postgresql://{self.dburi}", echo=False)
            if not database_exists(engine.url):
                create_database(engine.url)
            connections.append(engine.connect())
            sessionmaker(autocommit=False, autoflush=False, bind=engine)

            if thread == 0:
                meta = MetaData()
                meta.create_all(engine)

        # A chunk is a group of threads
        entries = len(overture.data)
        log.debug(f"There are {entries} entries in {infile}")
        chunk = round(entries / cores)

        if entries <= chunk:
            result = parquetThread(overture.data, connections[0])
            timer.stop()
            return True

        index = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            block = 0
            while block <= entries:
                if len(overture.data[block : block + chunk]) == 0:
                    continue
                log.debug("Dispatching Block %d:%d" % (block, block + chunk))
                result = executor.submit(
                    parquetThread,
                    overture.data[block : block + chunk],
                    connections[index],
                )
                block += chunk
                index += 1
            executor.shutdown()
        timer.stop()

    def importGeoJson(
        self,
        infile: str,
    ):
        """Import a GeoJson data file into a postgres database.

        Args:
            infile (str): The file to import

        Returns:
            (bool): Whether the import finished sucessfully
        """
        # load the GeoJson file
        file = open(infile, "r")
        # size = os.path.getsize(infile)
        # for line in file.readlines():
        #    print(line)
        data = geojson.load(file)

        future = None
        result = None
        index = 0
        connections = list()

        timer = Timer(text="importGeoJson() took {seconds:.0f}s")
        timer.start()

        # A chunk is a group of threads
        entries = len(data["features"])
        chunk = round(entries / cores)

        # For small files we only need one thread
        if entries <= chunk:
            result = importThread(data["features"], self.connections[0])
            timer.stop()
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
            block = 0
            while block <= entries:
                log.debug("Dispatching Block %d:%d" % (block, block + chunk))
                result = executor.submit(
                    importThread,
                    data["features"][block : block + chunk],
                    self.connections[index],
                )
                block += chunk
                index += 1
            executor.shutdown()
        timer.stop()

        return True


def main():
    """This main function lets this class be run standalone by a bash script."""
    parser = argparse.ArgumentParser(
        prog="config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Import data into a postgres database",
        epilog="""
        This should only be run standalone for debugging purposes.
        """,
    )
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Input data file")
    parser.add_argument("-u", "--uri", required=True, help="Database URI")
    args = parser.parse_args()

    if len(argv) <= 1:
        parser.print_help()
        quit()

    # if verbose, dump to the terminal.
    if args.verbose is not None:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

    # Create the database
    mi = MapImporter(args.uri)

    path = Path(args.infile)

    # And populate it with data
    if path.suffix == ".osm" or path.suffix == ".pbf":
        mi.importOSM(args.infile)
    elif path.suffix == ".geojson":
        mi.importGeoJson(args.infile)
    elif path.suffix == ".parquet":
        # Newer data from Overture has a suffix
        mi.importParquet(args.infile)
    else:
        # Older data from Overture lacked the suffix
        mi.importParquet(args.infile)
    log.info(f"Imported {args.infile} into {args.uri}")


if __name__ == "__main__":
    """This is just a hook so this file can be run standalone during development."""
    main()
