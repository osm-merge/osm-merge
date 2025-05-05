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
AUTOMAKE_OPTIONS = dejagnu
AM_LDFLAGS = $(BOOST_LIBS) -lpthread -lz
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
	$(BOOST_JSON_LIB)

noinst_LTLIBRARIES = libosm.la
libosm_la_SOURCES = libosm.cc libosm.hh osmobjects.cc osmobjects.hh
libosm_la_LIBADD = $(BOOST_LIBS)

# An executable for debugging convienince
bin_PROGRAMS = libosm-test
libosm_test_SOURCES = libosm-test.cc
libosm_test_LDADD = $(BOOST_LIBS) libosm.la

# FIXME: not quite ready to do this yet
# if ENABLE_PYTHON
# # FIXME: although this builds and imports into python, no classes
# # are shown, so doesn't work yet.
# EXT := $(shell python3-config --extension-suffix)
# DIR := $(shell python3-config --configdir)
# lib_LTLIBRARIES = libosm.la
# libosm_la_SOURCES = python.cc
# libosm_la_LIBADD = libosm.la \
# 	$(BOOST_LIBS) \
# 	$(PYTHON_LIBS) \
# 	$(BOOST_PYTHON_LIB)
# libosm_la_LDFLAGS = -module -avoid-version -no-undefined
# endif

