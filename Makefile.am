# Copyright (c) 2025 OpenStreetMap US
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

AUTOMAKE_OPTIONS = dejagnu subdir-objects
ACLOCAL_AMFLAGS = -I m4
PROJECTS = fastclip libosm
DOXYGEN := @DOXYGEN@
all:
	for dir in $(PROJECTS); do \
		cd $${dir}/ && make && cd ..; \
	done

if ENABLE_DOXYGEN
apidoc:
	cd docs && $(DOXYGEN)

update:
	rsync -avrp docs/apidocs/html/* osmmerge.org:/var/www/html/osm-merge/docs/
endif
