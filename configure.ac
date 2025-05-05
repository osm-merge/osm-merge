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
AC_INIT(osmmerge, 1.0dev)
dnl AM_INIT_AUTOMAKE([subdir-objects])
AM_INIT_AUTOMAKE()
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([fastclip/fastclip.cc])
AC_CONFIG_HEADERS([osmconfig.h])
dnl only configure in the top level directory
dnl AC_CONFIG_SUBDIRS
AC_PROG_CC
AC_PROG_CXX
AC_EXEEXT
AC_PROG_INSTALL
AC_ENABLE_SHARED
AC_DISABLE_STATIC

LT_INIT
LT_LANG([C++])

AX_BOOST_BASE(1.69)
AX_BOOST_IOSTREAMS
AX_BOOST_SYSTEM
AX_BOOST_FILESYSTEM
AX_BOOST_THREAD
AX_BOOST_LOG
AX_BOOST_LOG_SETUP
AX_BOOST_PROGRAM_OPTIONS
AX_BOOST_JSON
dnl C_LANG_POP(C++)

dnl libboost has a dependency on GDAL
CPPFLAGS+=" $(pkg-config --cflags gdal)"
LIBS+=" $(pkg-config --libs gdal)"

dnl libboost has a dependency on libbexpat
CPPFLAGS+=" $(pkg-config --cflags expat)"
LIBS+=" $(pkg-config --libs expat)"

dnl libboost has a dependency on libbzip2
CPPFLAGS+=" $(pkg-config --cflags bzip2)"
LIBS+=" $(pkg-config --libs bzip2)"

# Find the path for python modules
AM_PATH_PYTHON([3])

dnl FIXME: While this appears to build the plugin, and it import into python,
dnl it still doesn't actually work yet.
AC_ARG_ENABLE([python],
  AS_HELP_STRING([--enable-python],[Enable Python binding]), [], [enable_python=no])

if test x"${enable_python}" = x"yes"; then
  LIBS+=" $(python3-config --libs)"
  LIBS+=" $(python3-config --embed)"
  CPPFLAGS+=" $(python3-config --cflags)"
  AX_BOOST_PYTHON
  AC_DEFINE(USE_PYTHON, [1], [Enable Python binding])
fi
AM_CONDITIONAL(ENABLE_PYTHON, [ test x"${enable_python}" != x"no" ])

$(pkg-config --exists libxml++-5.0)
if test $? -gt 0 ; then
   CPPFLAGS+=" $(pkg-config --cflags libxml++-5.0)"
   LIBS+=" $(pkg-config --libs libxml++-5.0)"
else
  CPPFLAGS+=" $(pkg-config --cflags libxml++-3.0)"
  LIBS+=" $(pkg-config --libs libxml++-3.0)"
fi

AC_CHECK_FILE([/usr/lib64/libosmpbf.so], [has_osmpbf=yes], [has_osmpbf=yes])
if test "${has_osmpbf}" == "yes"; then
   LIBS+=" -losmpbf"
else
  AC_MSG_ERROR([You need to install libosmpbf!])
fi
AC_CHECK_FILE([/usr/lib64/libprotobuf.so], [has_protobuf=yes], [has_protobuf=yes])
if test "${has_protobuf}" == "yes"; then
   LIBS+=" -lprotobuf"
else
  AC_MSG_ERROR([You need to install libprotobuf!])
fi

dnl protobuf, osmpbf
AC_CONFIG_FILES([
fastclip/Makefile
libosm/Makefile
])

AC_OUTPUT

# Local Variables:
# c-basic-offset: 2
# tab-width: 2
# indent-tabs-mode: nil
# End:
