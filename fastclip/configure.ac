dnl
dnl Copyright (c) 2020, 2021, 2023 Humanitarian OpenStreetMap Team
dnl
dnl This file is part of Underpass.
dnl
dnl     Underpass is free software: you can redistribute it and/or modify
dnl     it under the terms of the GNU General Public License as published by
dnl     the Free Software Foundation, either version 3 of the License, or
dnl     (at your option) any later version.
dnl
dnl     Underpass is distributed in the hope that it will be useful,
dnl     but WITHOUT ANY WARRANTY; without even the implied warranty of
dnl     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
dnl     GNU General Public License for more details.
dnl
dnl     You should have received a copy of the GNU General Public License
dnl     along with Underpass.  If not, see <https:dnlwww.gnu.org/licenses/>.
dnl

AC_PREREQ(2.59c)
AC_INIT(fastclip, 1.0dev)
AM_INIT_AUTOMAKE
AC_CONFIG_SRCDIR([fastclip.cc])

dnl AC_CONFIG_HEADERS([config.h])
dnl AC_CONFIG_MACRO_DIR([macros])

AC_PROG_CC
AC_PROG_CXX
AC_EXEEXT
AC_PROG_INSTALL

LT_INIT
AX_BOOST_BASE(1.69)
AX_BOOST_IOSTREAMS
AX_BOOST_SYSTEM
AX_BOOST_FILESYSTEM
AX_BOOST_THREAD
AX_BOOST_LOG
AX_BOOST_JSON
AX_BOOST_PROGRAM_OPTIONS
dnl For some reason this test works on Fedora, and fails on Debian. For now
dnl hardcode it.
dnl AX_BOOST_REGEX
LIBS+=" -lboost_regex"

CPPFLAGS+=" $(pkg-config --cflags gdal)"
LIBS+=" $(pkg-config --libs gdal)"

AC_CONFIG_FILES([
Makefile
])

AC_OUTPUT

# Local Variables:
# c-basic-offset: 2
# tab-width: 2
# indent-tabs-mode: nil
# End:
