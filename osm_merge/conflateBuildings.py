#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 OpenStreetMap US
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
from sys import argv

import geojson
from codetiming import Timer
from cpuinfo import get_cpu_info
from geojson import Feature, FeatureCollection, Polygon, MultiPolygon
from osm_merge.dbextract import DBExtract
# from osm_merge.geosupport import GeoSupport
# from geosupport import GeoSupport
# from osm_rawdata.postgres import uriParser
from shapely import wkb, wkt
from shapely.geometry import Polygon, shape, Point
import geopandas as gpd
from progress.spinner import PixelSpinner
import math
from osm_merge.yamlfile import YamlFile

import osm_merge as om
rootdir = om.__path__[0]

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info["count"]


class ConflateBuildings(DBExtract):
    def __init__(
        self,
        uri: str = None,
        blduri: str = None,
    ):
        """This class conflates data that has been imported into a postgres
        database using the osm-rawdata schema.

        Args:
            uri (str): The DB URI for OSM data
            blduri (str): The DB URI for building footprints

        Returns:
            (ConflateBuildings): An instance of this object
        """
        # if blduri:
        #     self.blddb = DBExtract(blduri)

        self.abbrevs = dict()
        self.boundary = None
        self.filter = list()
        if uri:
            super().__init__("conflate")
        # self.create_tables()
            self.aoi = None
        self.yaml = None
        tmp = self.load_config()
        config = tmp.getEntries()
        self.abbrevs = config["tags"]

    def load_config (self,
                yamlspec: str = f"{rootdir}/abbreviations.yaml",
                ) -> dict:
        """
        Import a GeoJson AOI file into a geometry.

        Args:
            yamlspec (str): The YAML file to import

        Returns:
            (dict): the tags
            """

        return YamlFile(yamlspec)

    def load_aoi(self,
                filespec: str,
                ) -> MultiPolygon:
        """
        Import a GeoJson AOI file into a geometry.

        Args:
            filespec (str): The GeoJson file to import

        Returns:
            (MultiPolygon): The AOI geometry
        """
        file = open(filespec, "r")
        boundary = geojson.load(file)
        polys = list()
        for feature in boundary["features"]:
            polys.append(feature["geometry"])
        self.aoi = MultiPolygon(polys)

        return self.aoi

    def create_tables(self,
                    ):
        # Create the tables
        # sql = "CREATE EXTENSION postgis;"
        # result = self.curs.execute(sql)
        sql = f"DROP TABLE IF EXISTS public.nodes CASCADE; CREATE TABLE public.nodes (osm_id bigint, geom geometry, tags jsonb);"
        result = self.curs.execute(sql)
        sql = f"DROP TABLE IF EXISTS public.ways_line CASCADE; CREATE TABLE public.ways_line (osm_id bigint, geom geometry, tags jsonb);"
        result = self.curs.execute(sql)
        sql = f"DROP TABLE IF EXISTS public.poly CASCADE; CREATE TABLE public.ways_poly (osm_id bigint, geom geometry, tags jsonb);"
        result = self.curs.execute(sql)

    def importDataset(self,
                     filespec: str,
                     ) -> bool:
        """
        Import a GeoJson file into a postgres database for conflation.

        Args:
            filespec (str): The GeoJson file to import

        Returns:
            (bool): If the import was successful
        """
        file = open(filespec, "r")
        data = geojson.load(file)

        for entry in data["features"]:
            keys = "geom, "
            geometry = shape(entry["geometry"])
            ewkt = geometry.wkt
            if geometry.geom_type == "Polygon":
                table = "ways_poly"
            if geometry.geom_type == "Point":
                table = "nodes"
            tags = f"\'{{"
            for key, value in entry["properties"].items():
                print(f"FIXME: {key} = {value} {type(value)}")
                if type(value) == dict:
                    # breakpoint()
                    continue
                tags += f"\"{key}\": \"{value}\", "
            tags = tags[:-2]
            tags += "}\'::jsonb)"
            sql = f"INSERT INTO {table} (geom, tags) VALUES(ST_GeomFromEWKT(\'SRID=4326;{ewkt}\'), {tags}"
            print(sql)
            result = self.curs.execute(sql)

        return False

    def addSourceFilter(
        self,
        source: str,
    ):
        """Add to a list of suspect bad source datasets"""
        self.filter.append(source)

    def overlapDB(
        self,
        dburi: str,
    ):
        """
        Conflate buildings where all the data is in the same postgres database
        using the osm-rawdata schema.

        Args:
            dburi (str): The URI for the existing OSM data

        This is not fast for large areas!
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        # Find duplicate buildings in the same database
        # sql = f"DROP VIEW IF EXISTS overlap_view;CREATE VIEW overlap_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g2.osm_id AS id2,g2.geom as geom2 FROM {self.view} AS g1, {self.view} AS g2 WHERE ST_OVERLAPS(g1.geom, g2.geom) AND (g1.tags->>'building' IS NOT NULL AND g2.tags->>'building' IS NOT NULL)"
        # sql = "SELECT * FROM (SELECT ways_view.id, tags, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY ways_view.geom asc) AS Row, geom FROM ONLY ways_view) dups WHERE dups.Row > 1"
        # Make a new postgres VIEW of all overlapping or touching buildings
        # log.info(f"Looking for overlapping buildings in \"{self.uri['dbname']}\", this make take awhile...")
        # print(sql)
        # Views must be dropped in the right order
        sql = (
            "DROP TABLE IF EXISTS dups_view CASCADE; DROP TABLE IF EXISTS osm_view CASCADE;DROP TABLE IF EXISTS ways_view CASCADE;"
        )
        # result = self.db.queryDB(sql)

        if self.boundary:
            self.db.clipDB(self.boundary)

        log.debug("Clipping OSM database")
        # ewkt = shape(self.boundary)
        # uri = uriParser(dburi)
        # log.debug(f"Extracting OSM subset from \"{uri['dbname']}\"")
        # sql = f"CREATE TABLE osm_view AS SELECT osm_id,tags,geom FROM dblink('dbname={uri['dbname']}', 'SELECT osm_id,tags,geom FROM ways_poly') AS t1(osm_id int, tags jsonb, geom geometry) WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{ewkt}'), geom) AND tags->>'building' IS NOT NULL"
        # # print(sql)
        # result = self.db.queryDB(sql)

        sql = "CREATE TABLE dups_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g1.tags AS tags1,g2.osm_id AS id2,g2.geom as geom2, g2.tags AS tags2 FROM ways_view AS g1, osm_view AS g2 WHERE ST_INTERSECTS(g1.geom, g2.geom) AND g2.tags->>'building' IS NOT NULL"
        print(sql)
        result = self.osmdb.execute_query(sql)

    def cleanDuplicates(self) -> bool:
        """Delete the entries from the duplicate building view.

        Returns:
            (FeatureCollection): The entries from the datbase table
        """
        log.debug("Removing duplicate buildings from ways_view")
        sql = "DELETE FROM ways_view WHERE osm_id IN (SELECT id1 FROM dups_view)"

        result = self.db.queryDB(sql)
        return True

    def getNew(self) -> FeatureCollection:
        """
        Get only the new buildings

        Returns:
            (FeatureCollection): The entries from the database table
        """
        sql = "SELECT osm_id,geom,tags FROM ways_view"
        result = self.db.queryDB(sql)
        features = list()
        for item in result:
            # log.debug(item)
            entry = {"osm_id": item[0]}
            entry.update(item[2])
            geom = wkb.loads(item[1])
            features.append(Feature(geometry=geom, properties=entry))

        log.debug(f"{len(features)} new features found")
        return FeatureCollection(features)

    def findHighway(
        self,
        feature: Feature,
    ):
        """Find the nearest highway to a feature

        Args:
            feature (Feature): The feature to check against
        """
        pass

    def getDuplicates(self):
        """Get the entries from the duplicate building view.

        Returns:
            (FeatureCollection): The entries from the datbase table
        """
        sql = "SELECT area,id1,geom1,tags1,id2,geom2,tags2 FROM dups_view"
        result = self.db.queryDB(sql)
        features = list()
        for item in result:
            # log.debug(item)
            # First building identified
            entry = {"area": float(item[0]), "id": int(item[1])}
            geom = wkb.loads(item[2])
            entry.update(item[3])
            features.append(Feature(geometry=geom, properties=entry))

            # Second building identified
            entry = {"area": float(item[0]), "id": int(item[4])}
            entry["id"] = int(item[4])
            geom = wkb.loads(item[5])
            entry.update(item[6])
            # FIXME: Merge the tags from the buildings into the OSM feature
            # entry.update(item[3])
            features.append(Feature(geometry=geom, properties=entry))

        log.debug(f"{len(features)} duplicate features found")
        return FeatureCollection(features)

    def merge_address(self,
                       addresses: str,
                       footfile: str,
                       yaml: list,
                        ):
        """
        Conflate two geoJson files.

        Args:
            addressses (str): Colorado address data
            footfile (str): building footprints
            config (dict) Conversion data for address parsing
        """
        addrs = gpd.read_file(addresses)
        foot = gpd.read_file(footfile)

        spin = PixelSpinner('Processing...')

        tags = self.list_to_dict(yaml[0])
        convert = self.list_to_dict(yaml[1])
        addr_tag = convert["addr:fullname"]
        buildings = list()
        for feature in foot.iterfeatures():
            spin.next()
            if feature["geometry"] is None:
                continue
            node = shape(feature["geometry"])
            address = addrs.iloc[addrs.sindex.query(node, predicate="intersects")]
            if len(address["geometry"]) == 0:
                # log.debug(f"{feature} already in OSM")
                continue
            # log.debug(f"{address} not in OSM")
            row = address.values[0].view().tolist()
            address = dict(zip(tags["tags"], row))
            fullname = address[addr_tag]
            pos = fullname.find(' ')
            number = fullname[:pos]
            street = fullname[pos:].strip()
            props = {"addr:housenumber": number, "addr:street": self.expand_name(street), "building": "yes"}
            buildings.append(Feature(properties = props, geometry = shape(feature["geometry"])))

        fc = FeatureCollection(buildings)
        outfile = "merged_buildings.geojson"    
        file = open(outfile, "w")
        geojson.dump(fc, file, indent=4)
        log.info(f"Wrote {outfile}")

    def conflate_files(self,
                       osmfile: str,
                       footfile: str,
                           ):
        """
        Conflate two geoJson files.

        Args:
            osmfile (str): OSM building data extract
            footfile (str): Building footprints
        """
        osm = gpd.read_file(osmfile)
        foot = gpd.read_file(footfile)
        foot['savedindex']= foot.index #Save the index values as a new column
        #Find the polygons that intersect. Keep savedindex as a series
        intersecting = osm.sjoin(foot, how='inner')['savedindex']
        #Filter away these, "savedindex is not in intersecting"
        foot = foot[~foot.savedindex.isin(intersecting)]
        foot.to_file(r'new-buildings.geojson')

    def expand_name (self,
                    fullname : str,
                    ) -> str:
        """
        Expand all the abbreviations.
        """
        fixed = str()
        for word in fullname.split(' '):
            try:
                fixed += f" {self.abbrevs[word.capitalize()]} "
            except:
                fixed += f" {word.capitalize()} "

        return fixed.replace("  ", " ").strip()

    def list_to_dict (self,
                      data: dict,
                      ) -> dict:
        """
        Convert the list of dicts to one big dict, used for parsing YAML files.
        """
        new = dict()
        for tag, value in data.items():
            if type(value) == dict:
                breakpoint()
            if tag == "tags":
                new[tag] = value
            elif tag == "convert":
                for entry in value:
                    if type(entry) == dict:
                        [[k, v]] = entry.items()
                        new[k] = v

        return new

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflateDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features from OSM.",
        epilog="""
./conflateBuildings.py  -v -a /play/SourceData/Tasks/Colorado/Buildings/addr-JeffersonCounty.geojson  -f /tmp/new-buildings.geojson --help
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-f", "--footprints", help="Building footpints data Source")
    parser.add_argument("-o", "--osmdata",  help="OpenStreetMap data Source")
    parser.add_argument("-a", "--addresses",  help="Address data Source")
    parser.add_argument("-y", "--yaml",  help="YAML config file for address datasets")
    parser.add_argument("-b", "--boundary", help="Boundary polygon to limit the data size")
    # parser.add_argument("-g", "--geo", help="import GeoJson into database for conflation")
    # parser.add_argument("-o", "--outfile", help="Post conflation output file")

    # Need at least one operation
    if len(argv) == 1:
        parser.print_help()
        quit()

    args = parser.parse_args()

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(threadName)10s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        log.addHandler(ch)

    # SELECT * fROM ways_poly WHERE tags->>'capture_dates_range' IS NOT NULL;

    # if args.osmdata[:3] == "PG:":
    #     pass

    cdb = ConflateBuildings()
    if args.yaml:
        config = cdb.load_config (args.yaml)
        # print(config.yaml)

    if args.boundary:
        aoiwkt = cdb.load_aoi(args.boundary)

    if args.addresses:
        cdb.merge_address(args.addresses, args.footprints, config.yaml)

    if args.osmdata:
        cdb.conflate_files(args.osmdata, args.footprints)

        # cdb.create_tables()
    # cdb.overlapDB(args.osmuri)
    # features = cdb.getDuplicates()

    # FIXME: These are only for debugging
    # file = open("foo.geojson", "w")
    # geojson.dump(features, file)
    # log.info("Wrote foo.geojson for duplicates")

    # cdb.cleanDuplicates()
    # features = cdb.getNew()
    # file = open("bar.geojson", "w")
    # geojson.dump(features, file)

    # log.info("Wrote bar.geojson for new buildings")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
