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

import argparse
import glob
import logging
import os
import sys
from pathlib import Path

from osm_merge.fieldwork.parsers import ODKParsers
from osm_merge.osmfile import OsmFile

# Instantiate logger
log = logging.getLogger(__name__)


def main():
    """This is a program that reads in the ODK Instance file, which is in XML,
    and converts it to an OSM XML file so it can be viewed in an editor.
    """
    parser = argparse.ArgumentParser(description="Convert ODK XML instance file to OSM XML format")
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-y", "--yaml", help="Alternate YAML file")
    parser.add_argument("-x", "--xlsfile", help="Source XLSFile")
    parser.add_argument("-i", "--infile", required=True, help="The input file")
    parser.add_argument("-o","--outfile", default='out.osm',
                        help='The output file for JOSM')
    args = parser.parse_args()

    # if verbose, dump to the terminal
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )

    toplevel = Path(args.infile)
    odk = ODKParsers(args.yaml)
    odk.parseXLS(args.xlsfile)
    xmlfiles = list()
    data = list()
    # It's a wildcard, used for XML instance files
    if args.infile.find("*") >= 0:
        log.debug(f"Parsing multiple ODK XML files {args.infile}")
        toplevel = Path(args.infile[:-1])
        for dirs in glob.glob(args.infile):
            xml = os.listdir(dirs)
            full = os.path.join(dirs, xml[0])
            xmlfiles.append(full)
        for infile in xmlfiles:
            entry = odk.XMLparser(infile)
            # entry = odk.createEntry(tmp[0])
            data.append(entry)
    elif toplevel.suffix == ".xml":
        # It's an instance file from ODK Collect
        log.debug(f"Parsing ODK XML files {args.infile}")
        # There is always only one XML file per infile
        full = os.path.join(toplevel, os.path.basename(toplevel))
        xmlfiles.append(full + ".xml")
        tmp = odk.XMLparser(args.infile)
        # entry = odk.createEntry(tmp)
        data.append(entry)
    elif toplevel.suffix == ".csv":
        log.debug(f"Parsing csv files {args.infile}")
        for entry in odk.CSVparser(args.infile):
            data.append(entry)
    elif toplevel.suffix == ".json":
        log.debug(f"Parsing json files {args.infile}")
        for entry in odk.JSONparser(args.infile):
            data.append(entry)

    # Write the data
    osm = OsmFile()
    osm.writeOSM(data, args.outfile)
    log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
