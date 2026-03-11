# Copyright (c) 2025, 2026 OpenStreetMap US
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

FILES = buildings-nodata.xlsx \
	camping-nodata.xlsx \
	highways-nodata.xlsx \
	historical.xlsx

all: $(FILES)

# %.yaml: %.xlsx
%.xlsx: %.yaml
	-yxf -f $<

SUFFIXES: .xlsx .yaml
