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

SOURCES = fastclip.cc fastclip.hh

lib_LTLIBRARIES = libfastclip.la
libfastclip_la_SOURCES = $(SOURCES)
libfastclip_la_LIBADD = $(BOOST_LIBS)

# An executable for debugging convienince
# if ENABLE_STANDALONE
bin_PROGRAMS = fastclip
fastclip_SOURCES = main.cc
fastclip_LDADD = $(BOOST_LIBS) libfastclip.la
# endif

# if ENABLE_PYTHON
# EXT := $(shell python3-config --extension-suffix)
# DIR := $(shell python3-config --configdir)
# lib_LTIBRARIES = libfastclip.la
# libfastclip_la_SOURCES = python.cc
# libfastclip_la_LDADD = $(BOOST_LIBS) libosmmerge.la
# libfastclip_la_LDFLAGS = -module -avoid-version -no-undefined \
# 	$(BOOST_LIBS)
# 	$(PYTHON_LIBS) \
# 	$(BOOST_PYTHON_LIB)

# PY_OBJECTS = $(fastclip_la_OBJECTS:.lo=.o)
# install-python: fastclip.la
# 	if test x"$(prefix)" = x"/usr/lib" -a "$(shell whoami)" != "root"; then \
# 	    echo "Need to be root!"; \
# 	else \
# 	    moddir=$(shell dirname $(DIR))/lib-dynload; \
# 	    if test ! -e $${moddir}; then \
# 	        $(MDIR_P) $${moddir}; \
# 	    fi; \
# 	    cp .libs/libfastclip.so $${moddir}/libfastclip$(EXT); \
# 	fi

# endif

