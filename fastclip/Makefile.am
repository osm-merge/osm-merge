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

AM_CXXFLAGS = -g -std=c++17 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DBOOST_LOG_DYN_LINK

BOOST_LIBS = $(BOOST_DATE_TIME_LIB) \
	$(BOOST_SYSTEM_LIB) \
	$(BOOST_FILESYSTEM_LIB) \
	$(BOOST_LOG_LIB) \
	$(BOOST_PROGRAM_OPTIONS_LIB) \
	$(BOOST_IOSTREAMS_LIB) \
	$(BOOST_THREAD_LIB) \
	$(BOOST_JSON)

if ENABLE_PYTHON
BOOST_LIBS ++ $(BOOST_PYTHON)

# BOOST_LIBS=-lboost_program_options -lboost_log -lboost_log_setup -lboost_thread -lboost_json -l boot_python

AM_LDFLAGS = $(BOOST_LIBS) -lpthread -lz -lexpat -lbz2 -lsimdjson

bin_PROGRAMS = fastclip
fastclip_SOURCES = fastclip.cc fastclip.hh
fastclip_LDADD = $(BOOST_LIBS)

