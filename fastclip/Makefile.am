# Copyright (c) 2023 Humanitarian OpenStreetMap Team
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

# To avoid forcing people to use the autotools to configure
# and build, for now just assume all the dependencies are
# installed.
AM_CXXFLAGS = -g -std=c++17 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DBOOST_LOG_DYN_LINK

BOOST_LIBS=-lboost_program_options -lboost_log -lboost_log_setup -lboost_thread -lboost_json
AM_LDFLAGS = $(BOOST_LIBS) -lpthread -lz -lexpat -lbz2 -lsimdjson

bin_PROGRAMS = fastclip
fastclip_SOURCES = fastclip.cc fastclip.hh
fastclip_LDADD = $(BOOST_LIBS)

