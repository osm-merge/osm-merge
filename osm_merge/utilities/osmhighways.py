#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024, 2025 OpenStreetMap US
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

#
# This program is not fast, being 100% python, but it can handles very large
# files. I may convert it to C++ at some point if it becomes a problem. But
# it does produce an good file for conflation, which is the primary goal.
#

import argparse
import logging
import sys
import os
from sys import argv
from codetiming import Timer
from pathlib import Path
import osmium
from osmium.geom import GeoJSONFactory
import re
from shapely.geometry import shape
from shapely import prepare, from_geojson, from_wkt, contains, intersects, intersection, difference
from progress.spinner import Spinner
import geojson

# Instantiate logger
log = logging.getLogger(__name__)

def getRef(name) -> str:
    """
    Extract the reference number in the name string

    Args:
        name (str): The name of the highway

    Returns:
        (str): The reference number, which is an alphanumeric
    """
    if not name:
        # log.error(f"Nothing done, empty string")
        return name

    tmp = name.split(' ')
    return tmp[len(tmp) - 1:][0]

    # # The number is always (supposedly) last, so this gets all the
    # # weird contortions without getting complicated.
    # ref = "[0-9].*+"
    # pat = re.compile(ref)
    # result = pat.findall(name.lower())
    # if len(result) == 0:
    #     # if it's an integer, not decimals or character appended,
    #     # look for that too.
    #     ref = " [0-9]+"
    #     pat = re.compile(ref)
    #     result = pat.findall(name.lower())
    #     if len(result) == 0:
    #         return name
    #     else:
    #         return result[0].strip().replace(' ', '.')
    # else:
    #     if '/' in result[0]:
    #         return result[0]
    #     else:
    #         return result[0].replace(' ', '.')
    
def filterTags(obj):
    """
    Filter the tags, which entails fixing typos, abbreviations, etc...

    Args:
        obj: The feature to filter

    Returns:
    
    """
    fix = ["name", "name_1", "alt_name", "ref", "ref:usfs"]

    name = None
    newtags = dict()
    if "name" in obj.tags:
        name = obj.tags.get("name")
    # log.debug(f"NAME: {name}")

    for tag in obj.tags:
        matched = False
        key = tag[0]
        val = tag[1]
        # The OSM community has long ago decided these tags from the
        # TIGER import are useless, and should be deleted.
        if key[:6] == "tiger:":
            continue
        # Here's another import mess. The original MVUM data got imported
        # but all the original fields got add, often over a dozen. They
        # luckily all start with a _ character followed by an upper case
        # field name. OSM tags are always lower case. Delete all these tags.
        # Anything interesting like HIGH_CLEARANCE_VEHICLE=YES will
        # get added during conflation, so these fields aren't needed.
        pat = re.compile("^_[A-Z]+")
        if pat.match(key):
            continue
        if key not in fix:
            newtags[key] = val
            continue

        if key[:3] == "ref":
            if "ref" in newtags:
                newtags["ref"] += ';'
            else:
                newtags["ref"] = str()
            # A good ref has an FR or FS prefixed, so just use it, but move it
            # to the ref:usfs tag.
            if val[:3] == "FS " or val[:3] == "FR ":
                newtags["ref"] += val
                continue
            elif val[:4] == "FSR ":
                ref = getRef(val)
                newtags["ref"] += f"FR {ref}"
                continue
            elif key == "ref" and val[:3] == "CR ":
                pat = re.compile("county road")
                if pat.search(val.lower()):
                    newtags[key] += getRef(val)
                else:
                    newtags[key] += val
                continue
            ref = getRef(name)
            if ref and len(ref) > 0:
                # log.debug(f"MATCHED: {pat.pattern}")
                newtags["ref"] += f"FR {ref}"
            matched = True
            continue

        usfspats = ["fire road",
                    "fs.* road",
                    "f[sd]r ",
                    "usfsr ",
                    "fs[hr] ",
                    "usf.* road",
                    "national forest road",
                    "forest service road",
                    "fr ",
                    "fs ",
                    "forest road",
                    "usfs trail ",
                    ]
        pat = re.compile("county road")
        if key == "name" and name is not None:
            if pat.search(name.lower()):
                # breakpoint()
                ref = getRef(name)
                # log.debug(f"COUNTY: {pat.pattern} REF={ref.title()} NAME={name}")
                if ref and len(ref) > 0:
                    newtags["ref"] = f"CR {ref.title()}"
                continue
        # Often the County ref is in the name_1 column, which isn't supported
        # by OSM anyway.
        if key == "name_1":
            name = obj.tags.get("name_1").lower()
            pat = re.compile("county road")
            if pat.search(name):
                ref = getRef(name)
                # log.debug(f"COUNTY: {pat.pattern} REF={ref.title()} NAME={name}")
                if ref and len(ref) > 0:
                    newtags["ref"] = f"CR {ref.title()}"
                continue
        if key == "alt_name":
            name = obj.tags.get("alt_name").lower()
            pat = re.compile("county road")
            if pat.search(name):
                ref = getRef(name)
                # log.debug(f"COUNTY: {pat.pattern} REF={ref.title()} NAME={name}")
                if ref and len(ref) > 0:
                    newtags["ref"] = f"CR {ref.title()}"
                continue

            # FIXME: Since we're focused on roads in national forests or
            # parks, there shouldn't be any state or federal highways,
            # but you never know, this should be confirmed.
            # pat = re.compile("state highway")
            # pat = re.compile("united states highway")

            for regex in usfspats:
                pat = re.compile(regex)
                if pat.match(name.lower()):
                    for entry in name.split(';'):
                        ref = getRef(entry)
                        #log.debug(f"MATCHED: {pat.pattern} REF={ref.title()} NAME={name}")
                        if ref and len(ref) > 0:
                            if "ref" in newtags:
                                print(f"Adding a ; to {newtags["ref"]}")
                                newtags["ref"] += ';'
                            else:
                                newtags["ref"] = str()
                            newtags["ref"] += f"FR {ref.title()}"
                    matched = True
                    break
            if not matched:
                newtags[key] = val
        else:
            newtags[key] = val

    if "ref" in newtags and "ref:usfs" in newtags:
        newtags["ref"] = f"{newtags["ref"]};{newtags["ref:usfs"]}"
        del newtags["ref:usfs"]
    if "ref" not in obj.tags and "ref:usfs" in newtags:
        # breakpoint()
        newtags["ref"] = newtags["ref:usfs"]
        del newtags["ref:usfs"]
    # print(f"OLDTAGS: {len(obj.tags)}: {obj.tags}")
    # print(f"NEWTAGS: {len(newtags)} {newtags}")
    return newtags

def clip(boundary: str,
         infile: str,
         outfile: str,
         ):
    """
    Clip the data in a file by a multipolygon instead of using
    the command line program. The output file will only contain
    ways, in JOSM doing "File->update data' will load all the
    nodes so the highways are visible. It's slower of course
    than the C++ version, but this gives us better fine-grained
    control.

    Args:
        infile (str): The input data
        outfile (str): The output file
        boundary (str): The boundary

    Returns:
        (bool): Whether it worked or not
    """
    timer = Timer(text="clip() took {seconds:.0f}s")
    timer.start()

    # Load the boundary
    file = open(boundary, 'r')
    data = geojson.load(file)
    boundary = data["features"]
    task = shape(boundary[0]["geometry"])

    if os.path.exists(outfile):
        os.remove(outfile)
    nodes = set()
    # Pre-filter the ways by tags. The less object we need to look at, the better.
    way_filter = osmium.filter.KeyFilter('highway')
    # only scan the ways of the file
    spin = Spinner('Processing nodes...')
    fp = osmium.FileProcessor(infile, osmium.osm.WAY).with_filter(osmium.filter.KeyFilter('highway'))
    for obj in fp:
       spin.next()
       if "highway" in obj.tags:
           nodes.update(n.ref for n in obj.nodes)

    writer = osmium.SimpleWriter(outfile)

    # We need nodes and ways in the second pass.
    fab = GeoJSONFactory()
    spin = Spinner('Processing ways...')
    way_filter = osmium.filter.KeyFilter('highway').enable_for(osmium.osm.WAY)
    for obj in osmium.FileProcessor(infile, osmium.osm.WAY | osmium.osm.NODE).with_filter(way_filter).with_locations():
        spin.next()
        if obj.is_node() and obj.id in nodes:
            # We don't want POIs for barrier or crossing, just LineStrings
            if len(obj.tags) > 0:
                continue
            wkt = fab.create_point(obj)
            geom = shape(geojson.loads(wkt))
            # Add a node if it exists within the boundary
            if contains(task, geom) or intersects(task, geom):
                # writer.add(obj)
                # log.debug(f"Adding {obj.id}")
                continue
                # Strip the object of tags along the way
            # writer.add_node(obj.replace(tags={}))
        elif obj.is_way() and "highway" in obj.tags:
            wkt = fab.create_linestring(obj.nodes)
            geom = shape(geojson.loads(wkt))
            if contains(task, geom) or intersection(task, geom):
                writer.add_way(obj)
    timer.stop()
    return True

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts highways from OSM",
        epilog="""
This program extracts all the highways from an OSM file, and correct as
many of the bugs with names that are actually a reference number. 

    For Example: 
        osmhighways.py -v -i colorado-latest.osm.pbf -o co-highways.osm
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input file")
    parser.add_argument("-o", "--outfile", default="out.osm", help="Output file")
    # parser.add_argument("-c", "--clip", help="Clip file by polygon")
    # parser.add_argument("-s", "--small", help="Small dataset")

    args = parser.parse_args()
    # if verbose, dump to the terminal.
    log_level = os.getenv("LOG_LEVEL", default="INFO")
    if args.verbose is not None:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format=("%(asctime)s.%(msecs)03d [%(levelname)s] " "%(name)s | %(funcName)s:%(lineno)d | %(message)s"),
        datefmt="%y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # if args.clip:
    #     # cachefile = os.path.basename(args.infile.replace(".pbf", ".cache"))
    #     # create_nodecache(args.infile, cachefile)
    #     if not clip:
    #         log.error(f"You must specify a boundary!")
    #         parser.print_help()
    #         quit()
    #     if not args.infile:
    #         log.error(f"You must specify the input file!")
    #         parser.print_help()
    #         quit()

    #     clip(args.clip, args.infile, args.outfile)
    #     log.info(f"Wrote clipped file {args.outfile}")
    #     quit()

    # FIXME: this should change
    outfile = args.outfile
    keep = ["track",
            "unclassified",
            "residential",
            "primary",
            "secondary",
            "tertiary",
            "trunk",
            "motorway",
            "service",
            "path",
            ]
    spin = Spinner('Processing...')
    fp = osmium.FileProcessor(args.infile).with_filter(osmium.filter.KeyFilter('highway'))
    with osmium.BackReferenceWriter(outfile, ref_src=args.infile, overwrite=True) as writer:
        for obj in fp:
            spin.next()
            if obj.tags['highway'] in keep and obj.is_way():
                tags = filterTags(obj)
                writer.add(obj.replace(tags=tags))
    log.info(f"Wrote {outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
