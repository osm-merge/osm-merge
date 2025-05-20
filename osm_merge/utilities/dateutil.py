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
# This program proccesses the National Forest Service datasets. That
# processing includes deleting unnecessary tags, and converting the
# tags to an OSM standard for conflation.
#

import argparse
import logging
import sys
import os
import re
from datetime import datetime
import fiona

import osm_merge as om
rootdir = om.__path__[0]

# Instantiate logger
log = logging.getLogger(__name__)

def parse_opening_hours(datesopen: str) -> str:
    """
    Parse the string from the external dataset to OSM format.

    Args:
        datesopen (str): The string from the external dataset

    Returns:
        (str): The formatted string for OSM
    """
    months = {1: "Jan",
              2: "Feb",
              3: "Mar",
              4: "Apr",
              5: "May",
              6: "Jun",
              7: "Jul",
              8: "Aug",
              9: "Sep",
              10: "Oct",
              11: "Nov",
              12: "Dec",
              }
    opening_hours = str()
    # it's seasonal=no
    if not datesopen or datesopen == "01/01-12/31" or len(datesopen) < 11:
        return str()

    # Date ranges start with the first of the month, and end with
    # the last day of the month.
    dates = datesopen.split('-')
    start = dates[0].split('/')[0]
    try:
        end = dates[1].split('/')[0]
    except:
        breakpoint()
    try:
        opening_hours = f"{months[int(start)]}-{months[int(end)]}"
    except:
        breakpoint()
    return opening_hours

def count_lines(self,
                filespec: str,
                ) -> int:
    """
    Count the records in the data file.

    Args:
        filespec (str): The input data file name

    Returns:
        (int): The number of lines in the file
    """
    if not os.path.exists(filespec):
        logging.error(f"{filespec} doesn't exist!")
        return -1

    # data = fiona.open(filespec, "r")
    with fiona.open(filespec, 'r') as fp:
        for count, line in enumerate(fp):
            pass
        fp.close()
        return count
