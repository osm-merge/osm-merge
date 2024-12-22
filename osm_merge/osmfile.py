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

import argparse
import logging
import os
import sys
from datetime import datetime
from sys import argv
import html
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load, LineString
import geojson
import xmltodict

# Instantiate logger
log = logging.getLogger(__name__)


class OsmFile(object):
    """OSM File output."""

    def __init__(
        self,
        filespec: str = None,
        options: dict = None,
        outdir: str = "/tmp/",
    ):
        """This class reads and writes the OSM XML formated files.

        Args:
            filespec (str): The input or output file
            options (dict): Command line options
            outdir (str): The output directory for the file

        Returns:
            (OsmFile): An instance of this object
        """
        if options is None:
            options = dict()
        self.options = options
        # Read the config file to get our OSM credentials, if we have any
        # self.config = config.config(self.options)
        self.version = 3
        self.visible = "true"
        self.osmid = -1
        # Open the OSM output file
        self.file = None
        if filespec is not None:
            self.file = open(filespec, "w")
            # self.file = open(filespec + ".osm", 'w')
            logging.info("Opened output file: " + filespec)
        self.header()
        # logging.error("Couldn't open %s for writing!" % filespec)

        # This is the file that contains all the filtering data
        # self.ctable = convfile(self.options.get('convfile'))
        # self.options['convfile'] = None
        # These are for importing the CO addresses
        self.full = None
        self.addr = None
        # decrement the ID
        self.start = -1
        # path = xlsforms_path.replace("xlsforms", "")
        self.data = list()

    def __del__(self):
        """Close the OSM XML file automatically."""
        # log.debug("Closing output file")
        self.footer()

    def isclosed(self):
        """Is the OSM XML file open or closed ?

        Returns:
            (bool): The OSM XML file status
        """
        return self.file.closed

    def header(self):
        """Write the header of the OSM XML file."""
        if self.file is not None:
            self.file.write("<?xml version='1.0' encoding='UTF-8'?>\n")
            self.file.write('<osm version="0.6" generator="osm-merge 0.3">\n')
            self.file.flush()

    def footer(self):
        """Write the footer of the OSM XML file."""
        # logging.debug("FIXME: %r" % self.file)
        if self.file is not None:
            self.file.write("</osm>\n")
            self.file.flush()
            if self.file is False:
                self.file.close()
        self.file = None

    def loadFile(
        self,
        osmfile: str,
    ) -> list:
        """
        Read a OSM XML file and convert it to GeoJson for consistency.

        Args:
            osmfile (str): The OSM XML file to load

        Returns:
            (list): The entries in the OSM XML file
        """
        alldata = list()
        size = os.path.getsize(osmfile)
        with open(osmfile, "r") as file:
            xml = file.read(size)
            doc = xmltodict.parse(xml)
            if "osm" not in doc:
                logging.warning("No data in this instance")
                return False
            data = doc["osm"]
            if "node" not in data:
                logging.warning("No nodes in this instance")
                return False

        nodes = dict()
        for node in data["node"]:
            properties = {
                "id": int(node["@id"]),
            }
            if "@version" not in node:
                properties["version"] = 1
            else:
                properties["version"] = node["@version"]

            if "@timestamp" in node:
                properties["timestamp"] = node["@timestamp"]

            if "tag" in node:
                for tag in node["tag"]:
                    if type(tag) == dict:
                        # Drop all the TIGER tags based on
                        # https://wiki.openstreetmap.org/wiki/TIGER_fixup
                        if tag["@k"] in properties:
                            if properties[tag["@k"]][:7] == "tiger:":
                                continue
                        properties[tag["@k"]] = tag["@v"].strip()
                        # continue
                    else:
                        properties[node["tag"]["@k"]] = node["tag"]["@v"].strip()
                    # continue
            geom = Point((float(node["@lon"]), float(node["@lat"])))
            # cache the nodes so we can dereference the refs into
            # coordinates, but we don't need them in GeoJson format.
            nodes[properties["id"]] = geom
            if len(properties) > 2:
                self.data.append(Feature(geometry=geom, properties=properties))

        for way in data["way"]:
            attrs = dict()
            properties = {
                "id": int(way["@id"]),
            }
            refs = list()
            if "nd" in way:
                if len(way["nd"]) > 0:
                    for ref in way["nd"]:
                        refs.append(int(ref["@ref"]))
                properties["refs"] = refs

            if "@version" not in node:
                properties["version"] = 1
            else:
                properties["version"] = node["@version"]

            if "@timestamp" in node:
                attrs["timestamp"] = node["@timestamp"]

            if "tag" in way:
                for tag in way["tag"]:
                    if type(tag) == dict:
                        properties[tag["@k"]] = tag["@v"].strip()
                        # continue
                    else:
                        properties[way["tag"]["@k"]] = way["tag"]["@v"].strip()
                    # continue
            # geom =
            tmp = list()
            for ref in refs:
                tmp.append(nodes[ref]['coordinates'])
            geom = LineString(tmp)
            if geom is None:
                breakpoint()
            # log.debug(f"WAY: {properties}")
            self.data.append(Feature(geometry=geom, properties=properties))

        return self.data

    def writeOSM(self,
                 data: list,
                 ):
        """
        Write the data to an OSM XML file.

        Args:
            data (list): The list of GeoJson features
        """
        negid = -100
        id = -1
        out = str()
        newmvum = list()
        for entry in data:
            version = 1
            tags = entry["properties"]
            if "osm_id" in tags:
                id = tags["osm_id"]
            elif "id" in tags:
                id = tags["id"]
            elif "id" not in tags:
                # There is no id or version for non OSM features
                id -= 1
            if "version" in entry["properties"]:
                version = int(entry["properties"]["version"])
                version += 1
            # if id == 814085818:
            #    breakpoint()
            attrs = {"id": id, "version": version}
            # These are OSM attributes, not tags
            if "id" in tags:
                del tags["id"]
            if "version" in tags:
                del tags["version"]
            item = {"attrs": attrs, "tags": tags}
            # if entry["geometry"]["type"] == "LineString" or entry["geometry"]["type"] == "Polygon":
            # print(entry)
            out = str()
            if entry["geometry"] is not None and entry["geometry"]["type"] == "Point":
                # It's a node referenced by a way
                item["attrs"]["lon"] = entry["geometry"]["coordinates"][0]
                item["attrs"]["lat"] = entry["geometry"]["coordinates"][1]
                if "timestamp" in item["tags"]:
                    item["attrs"]["timestamp"] = item["tags"]["timestamp"]
                    del item["tags"]["timestamp"]
                # referenced nodes should have no tags
                del item["tags"]
                # FIXME: determine if we need to write nodes
                # out = osm.createNode(item, False)
                continue
            else:
                # OSM ways don't have a geometry, just references to node IDs.
                # The OSM XML file won't have any nodes, so at first won't
                # display in JOSM until you do a File->"Update modified",
                if "refs" not in tags:
                    # log.debug(f"No Refs, so new MVUM road not in OSM {tags}")
                    # tags["fixme"] = "New road from MVUM, don't add!"
                    # FIXME: for now we don't do anything with new roads from
                    # an external dataset, because that would be an import.
                    newmvum.append(entry)
                    continue
                if len(tags['refs']) > 0:
                    if type(tags["refs"]) != list:
                        item["refs"] = eval(tags["refs"])
                    else:
                        item["refs"] = tags["refs"]
                    del tags["refs"]
                    out = osm.createWay(item, True)
            if len(out) > 0:
                osm.write(out)

    def createWay(
        self,
        way: dict,
        modified: bool = False,
    ):
        """This creates a string that is the OSM representation of a node.

        Args:
            way (dict): The input way data structure
            modified (bool): Is this a modified feature ?

        Returns:
            (str): The OSM XML entry
        """
        attrs = dict()
        osm = ""

        # Add default attributes
        if modified:
            attrs["action"] = "modify"
        if "osm_way_id" in way["attrs"]:
            attrs["id"] = int(way["attrs"]["osm_way_id"])
        elif "osm_id" in way["attrs"]:
            attrs["id"] = int(way["attrs"]["osm_id"])
        elif "id" in way["attrs"]:
            attrs["id"] = int(way["attrs"]["id"])
        else:
            attrs["id"] = self.start
            self.start -= 1
        if "version" not in way["attrs"]:
            attrs["version"] = 1
        else:
            attrs["version"] = way["attrs"]["version"]
        attrs["timestamp"] = datetime.now().strftime("%Y-%m-%dT%TZ")
        # If the resulting file is publicly accessible without authentication, The GDPR applies
        # and the identifying fields should not be included
        if "uid" in way["attrs"]:
            attrs["uid"] = way["attrs"]["uid"]
        if "user" in way["attrs"]:
            attrs["user"] = way["attrs"]["user"]

        # Make all the nodes first. The data in the track has 4 fields. The first two
        # are the lat/lon, then the altitude, and finally the GPS accuracy.
        # newrefs = list()
        node = dict()
        node["attrs"] = dict()
        # The geometry is an EWKT string, so there is no need to get fancy with
        # geometries, just manipulate the string, as OSM XML it's only strings
        # anyway.
        # geom = way['geom'][19:][:-2]
        # print(geom)
        # points = geom.split(",")
        # print(points)

        # epdb.st()
        # loop = 0
        # while loop < len(way['refs']):
        #     #print(f"{points[loop]} {way['refs'][loop]}")
        #     node['timestamp'] = attrs['timestamp']
        #     if 'user' in attrs and attrs['user'] is not None:
        #         node['attrs']['user'] = attrs['user']
        #     if 'uid' in attrs and attrs['uid'] is not None:
        #         node['attrs']['uid'] = attrs['uid']
        #     node['version'] = 0
        #     lat,lon = points[loop].split(' ')
        #     node['attrs']['lat'] = lat
        #     node['attrs']['lon'] = lon
        #     node['attrs']['id'] = way['refs'][loop]
        #     osm += self.createNode(node) + '\n'
        #     loop += 1

        # Processs atrributes
        line = ""
        for ref, value in attrs.items():
            line += "%s=%r " % (ref, str(value))
        osm += "  <way " + line + ">"

        if "refs" in way:
            for ref in way["refs"]:
                osm += '\n    <nd ref="%s"/>' % ref
        if "tags" in way:
            for key, value in way["tags"].items():
                if value is None:
                    continue
                if key == "track":
                    continue
                if key not in attrs:
                    newkey = html.escape(key)
                    newval = html.escape(str(value))
                    osm += f"\n    <tag k='{newkey}' v='{newval}'/>"
            if modified:
                osm += '\n    <tag k="note" v="Do not upload this without validation!"/>'
            osm += "\n"
        osm += "  </way>\n"

        return osm

    def featureToNode(
        self,
        feature: dict,
    ):
        """Convert a GeoJson feature into the data structures used here.

        Args:
            feature (dict): The GeoJson feature to convert

        Returns:
            (dict): The data structure used by this file
        """
        osm = dict()
        ignore = ("label", "title")
        tags = dict()
        attrs = dict()
        for tag, value in feature["properties"].items():
            if tag == "id":
                attrs["osm_id"] = value
            elif tag not in ignore:
                tags[tag] = value
        coords = feature["geometry"]["coordinates"]
        attrs["lat"] = coords[1]
        attrs["lon"] = coords[0]
        osm["attrs"] = attrs
        osm["tags"] = tags
        return osm

    def createNode(
        self,
        node: dict,
        modified: bool = False,
    ):
        """This creates a string that is the OSM representation of a node.

        Args:
            node (dict): The input node data structure
            modified (bool): Is this a modified feature ?

        Returns:
            (str): The OSM XML entry
        """
        attrs = dict()
        # Add default attributes
        if modified:
            attrs["action"] = "modify"

        if "id" in node["attrs"]:
            attrs["id"] = int(node["attrs"]["id"])
        else:
            attrs["id"] = self.start
            self.start -= 1
        if "version" not in node["attrs"]:
            attrs["version"] = "1"
        else:
            attrs["version"] = int(node["attrs"]["version"]) + 1
        attrs["lat"] = node["attrs"]["lat"]
        attrs["lon"] = node["attrs"]["lon"]
        attrs["timestamp"] = datetime.now().strftime("%Y-%m-%dT%TZ")
        # If the resulting file is publicly accessible without authentication, THE GDPR applies
        # and the identifying fields should not be included
        if "uid" in node["attrs"]:
            attrs["uid"] = node["attrs"]["uid"]
        if "user" in node["attrs"]:
            attrs["user"] = node["attrs"]["user"]

        # Processs atrributes
        line = ""
        osm = ""
        for ref, value in attrs.items():
            line += "%s=%r " % (ref, str(value))
        osm += "  <node " + line

        if "tags" in node:
            osm += ">"
            for key, value in node["tags"].items():
                if not value:
                    continue
                if key not in attrs:
                    newkey = html.escape(key)
                    newval = html.escape(str(value))
                    osm += f"\n    <tag k='{newkey}' v='{newval}'/>"
            osm += "\n  </node>\n"
        else:
            osm += "/>"

        return osm

    def createTag(
        self,
        field: str,
        value: str,
    ):
        """Create a data structure for an OSM feature tag.

        Args:
            field (str): The tag name
            value (str): The value for the tag

        Returns:
            (dict): The newly created tag pair
        """
        newval = str(value)
        newval = newval.replace("&", "and")
        newval = newval.replace('"', "")
        tag = dict()
        # logging.debug("OSM:makeTag(field=%r, value=%r)" % (field, newval))

        newtag = field
        change = newval.split("=")
        if len(change) > 1:
            newtag = change[0]
            newval = change[1]

        tag[newtag] = newval
        return tag

    def dump(self):
        """Dump internal data structures, for debugging purposes only."""
        for entry in self.data:
            if entry["geometry"]["type"] == 'Point':
                print("Node")
            else:
                print("Way")
            for key, value in entry["properties"].items():
                print(f"\t{key} = {value}")

    def getFeature(
        self,
        id: int,
    ):
        """Get the data for a feature from the loaded OSM data file.

        Args:
            id (int): The ID to retrieve the feasture of

        Returns:
            (dict): The feature for this ID or None
        """
        return self.data[id]

    def getFields(self):
        """Extract all the tags used in this file."""
        fields = list()
        for _id, item in self.data.items():
            keys = list(item["tags"].keys())
            for key in keys:
                if key not in fields:
                    fields.append(key)
        # print(fields)


if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    # Command Line options
    parser = argparse.ArgumentParser(description="This program conflates ODK data with existing features from OSM.")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-o", "--osmfile", required=True, help="OSM XML file created by Osm-Fieldwork")
    args = parser.parse_args()

    # This program needs options to actually do anything
    if len(argv) == 1:
        parser.print_help()
        quit()

    # if verbose, dump to the terminal.
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )

    osm = OsmFile()
    osm.loadFile(args.osmfile)
    osm.dump()
