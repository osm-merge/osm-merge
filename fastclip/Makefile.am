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

ACLOCAL_AMFLAGS = -I m4

AM_CXXFLAGS = -g -std=c++17 \
	-D_LARGEFILE_SOURCE \
	-DBOOST_LOG_DYN_LINK \
	-D_FILE_OFFSET_BITS=64 \
	-Wno-switch

BOOST_LIBS = \
	$(BOOST_PROGRAM_OPTIONS_LIB) \
	$(BOOST_LOG_LIB) \
	$(BOOST_LOG_SETUP_LIB) \
	$(BOOST_THREAD_LIB) \
	$(BOOST_JSON_LIB) \
	$(BOOST_PYTHON_LIB)

if ENABLE_PYTHON
	WRAPPER = python.cc
endif

foo:
	@echo $(BOOST_LIBS)

AM_LDFLAGS = $(BOOST_LIBS) -lpthread -lz

bin_PROGRAMS = fastclip
fastclip_SOURCES = fastclip.cc fastclip.hh $(WRAPPER)
fastclip_LDADD = $(BOOST_LIBS)

