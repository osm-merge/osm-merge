# Copyright (c) 2020, 2021, 2022, 2023 Humanitarian OpenStreetMap Team
#
# This file is part of OSM-Fieldwork.
#
#     Osm-Fieldwork is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Osm-Fieldwork is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with Osm-Fieldwork.  If not, see <https:#www.gnu.org/licenses/>.
#

XLSFILES = $(shell ls *.xls)
XMLFILES = $(XLSFILES:.xls=.xml)

all: $(XMLFILES)

STAMPDIR=/tmp

# Convert XLSForm to XForm
%.xml : %.xls
	@xls2xform --pretty_print $<
	@echo "Generating $<"

%.stamp : %.xls
	stamp=$(STAMPDIR)/odk-$@; \
	touch $${stamp}; \
	echo "Generating $${stamp}"

# Generate all XForms
xform: $(XMLFILES)

# Cleanup the mess
clean: 
	rm -f *.xml *.geojson

force:

.SUFFIXES: .xml .xls
