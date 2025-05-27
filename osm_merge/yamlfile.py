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
import sys
import os

import yaml

# Instantiate logger
log = logging.getLogger(__name__)

class YamlFile(object):
    """Config file in YAML format."""

    def __init__(
        self,
        filespec: str,
    ):
        """This parses a yaml file into a dictionary for easy access.

        Args:
            filespec (str): The filespec of the YAML file to read

        Returns:
            (YamlFile): An instance of this object
        """
        self.filespec = None
        # if data == str:
        self.filespec = filespec
        self.file = open(filespec, "rb").read()
        self.yaml = yaml.load(self.file, Loader=yaml.Loader)
        self.data = dict()
        # self.getEntries()

    def get(self,
            keyword: str,
            tag: str = None,
            ):
        """
        Get the values for a top level keyword\

        Args:
            keyword (str): The top level keyword to get the values for
            tag (str): The category for the tag/values

        Returns:
            (dict): The values for the top level keyword
        """
        return self.yaml[keyword][tag]

    def getEntries(self):
        """
        Convert the list from the YAML file into a searchable data structure

        Returns:
            (dict): The parsed config file
        """
        columns = list()
        for entry in self.yaml:
            for key, values in entry.items():
                self.data[key] = dict()
                # values is a list of dicts which are tag/value pairs
                for item in values:
                    [[k, v]] = item.items()
                    if type(v) == str:
                        self.data[key][k] = v
                    elif type(v) == float or type(v) == int:
                        self.data[key][k] = str(v)
                    elif type(v) == list:
                        self.data[key][k] = dict()
                        for newval in v:
                            if newval is None:
                                continue
                            if type(newval) == dict:
                                [[k2, v2]] = newval.items()
                                if type(v2) == str:
                                    self.data[key][k].update(newval)
                                elif type(v2) == list:
                                    self.data[key][k][k2] = dict()
                                    for xxx in v2:
                                        [[k3, v3]] = xxx.items()
                                        if type(v3) == list:
                                            self.data[key][k][k2][k3] = dict()
                                            for foo in v3:
                                                self.data[key][k][k2][k3].update(foo)
                                            pass
                                        else:
                                            self.data[key][k][k2].update(xxx)
                    else:
                        log.error(f"{type(v)} is not suported.")

        # breakpoint()
        return self.data
    
    def dump(self):
        """Dump internal data structures, for debugging purposes only."""
        if self.filespec:
            print("YAML file: %s" % self.filespec)
        for key, values in self.data.items():
            print(f"Key is: {key}")
            for k, v in values.items():
                print(f"\t{k} = {v}")
            print("------------------")

#
# This script can be run standalone for debugging purposes. It's easier to debug
# this way than using pytest,
#
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    parser = argparse.ArgumentParser(description="Read and parse a YAML file")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, default="./xforms.yaml", help="The YAML input file")
    args, known = parser.parse_known_args()

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

    yaml1 = YamlFile(args.infile)

    x = yaml1.getEntries()
    yaml1.dump()
