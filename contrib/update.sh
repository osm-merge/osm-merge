#!/bin/bash

# Copyright (C) 2024 Humanitarian OpenstreetMap Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

# This script processes multiple boundaries to create the data extracts
# for every task being setup for the HOT Tasking Manager.

states="Utah Colorado Wyoming"

# Top level for boundaries, obviously system specific
boundaries="../../Boundaries/"

# FIXME: script in the utilities directory don't get install by pip
fixname="~/projects/HOT/osm-merge.git/trails/utilities/fixnames.py"
tmsplitter="/home/rob/projects/HOT/osm-merge.git/test/utilities/tm-splitter.py"

dryrun=""		     # echo

# The base datasets
osmdata="../wy-co-ut.osm"
mvumhighways="../Road_MVUM-out.geojson"
mvumtrails="../Trail_MVUM-out.geojson"
topohighways="../USGS_Topo_Roads-out.geojson"
topotrails="../USGS_Topo_Trails-out.geojson"

utah="Dixie_National_Forest \
      Bryce_Canyon_National_Park \
      Zion_National_Park \
      Capitol_Reef_National_Park \
      Arches_National_Park \
      Manti_La_Sal_National_Forest"

colorado="Arapaho_and_Roosevelt_National_Forests \
          Medicine_Bow_Routt_National_Forest \
          Grand_Mesa_Uncompahgre_and_Gunnison_National_Forests \
          Rio_Grande_National_Forest \
          San_Juan_National_Forest \
          Rocky_Mountain_National_Park"

wyoming="Bighorn_National_Forest \
         Bridger_Teton_National_Forest \
         Ashley_National_Forest \
         Caribou_Targhee_National_Forest \
         Shoshone_National_Forest \
         Black_Hills_National_Forest \
         Yellowstone_National_Park \
         Grand_Teton_National_Park"

# FIXME: figure why this isn't accessible in a bash function
declare -gA datasets
datasets["Utah"]="${utah}"
datasets["Colorado"]="${colorado}"
datasets["Wyoming"]="${wyoming}"

# declare -p ${datasets}

source="USFS_MVUM_Roads \
        USFS_MVUM_Trails \
        USFS_Trails \
        USFS_MVUM \
        USGS_Topo_Roads \
        USGS_Topo_Trails \
        OSM_Highways"

basesets="no"

split_aoi() {
    # fmtm-spliiter is available from here: https://hotosm.github.io/fmtm-splitter/
    tmmax=70000
    echo "Splitting ${1} into squares with ${tmmax} per side"
    for state in ${states}; do
	echo "Processing ${state} public lands..."
	for land in ${datasets["${state}"]}; do
	    echo "    Making TM sized projects for ${land}"
	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		aoi="${boundaries}/NationalParks/${land}.geojson"
	    else
		aoi="${boundaries}/NationalForests/${land}.geojson"
	    fi
	    # fmtm-splitter -v -b ${aoi} -m ${tmmax}
	    # This generates a grid of roughly 5000sq km tasks,
	    # which is the maximum TM supports. Some areas are
	    # smaller than this, so only one polygon.
	    ${tmsplitter} --grid --infile ${aoi} --threshold 0.7
	    # Make a multipolygon even if just one task
	    ogr2ogr -nlt MULTIPOLYGON -makevalid -clipsrc ${aoi} ${state}/${land}_Tasks.geojson output.geojson
	    echo "Wrote ${state}/${land}_Tasks.geojson"
	done
    done
}

make_sub_tasks() {
    # Split the polygon of the task into smaller sizes, each to fit
    # a small TM task. These are used to make small task sized
    # data extracts of the post conflated data to avoid lots of
    # cut & paste.
    tmmax=8000
    for state in ${states}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    echo "    Making task boundaries for clipping to ${land}"
	    for task in ${state}/${land}_Tasks/${land}*_Tasks*.geojson; do
		num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		base=$(echo ${task} | cut -d '.' -f 1)
		short=$(basename ${base} | sed -e "s/National.*Tasks/Task/")
		if test ! -e ${base}; then
		    mkdir -p ${base}
		fi
		# fmtm-splitter -v -b ${task} -m ${tmmax}
		echo "    Making sub task boundaries for ${task}"
		${tmsplitter} --grid --infile ${task} --threshold 0.1
		ogr2ogr -nlt MULTIPOLYGON -makevalid -clipsrc ${task} ${base}/${short}_Tasks.geojson output.geojson
		${tmsplitter} -v --split --infile ${base}/${short}_Tasks.geojson
		mv -f ${short}*.geojson ${base}
	    done
	done
    done
}

make_tasks() {
    # Split the multipolygon from fmtm-splitter into indivigual files
    # for ogr2ogr and osmium.
    for state in ${states}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    echo "    Making task boundaries for clipping to ${land}"
	    ${tmsplitter} -v -s -i ${state}/${land}_Tasks.geojson
	    mv ${land}_Tasks*.geojson ${state}/${land}_Tasks/
	done
    done	
}

make_sub_mvum() {
    for state in ${states}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    echo "    Making task boundaries for clipping to ${land}"
	    for task in ${state}/${land}_Tasks/${land}*_Tasks*.geojson; do
		echo "FOO"
		${dryrun} echo ogr2ogr -explodecollections -makevalid -clipsrc ${task} ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson ${state}/${land}_Tasks/mvum.geojson
	    done
	done
    done
}

make_mvum_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    base="${1-yes}"
    tasks="${2-yes}"
    for state in ${states}; do
     	echo "Processing MVUM data in ${state}..."
     	for land in ${datasets["${state}"]}; do
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    else
		clip="NationalForests"
	    fi
	    if test x"${base}" == x"yes"; then
		rm -f ${land}_Tasks/${land}_MVUM_Roads.geojson
		echo "    Making ${land}_MVUM_Roads.geojson"
		ogr2ogr -explodecollections -makevalid -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson ${mvumhighways}

		echo "    Making ${land}_MVUM_Trails.geojson"
		rm -f ${forest}_Tasks/${land}_MVUM_Trails.geojson
		${dryrun} ogr2ogr -explodecollections -makevalid -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson ${mvumtrails}

		# Merge the MVUM roads and trails together, since in OSM they
		# are both in the data extract used for vconflation.
		echo "    Merging MVUM Trails and Roads together"
		rm -f ${state}/${land}_Tasks/mvum.geojson
		${dryrun} ogrmerge.py -nln mvum -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
		${dryrun} ogrmerge.py -nln mvum -append -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
	    fi

	    if test x"${tasks}" == x"yes"; then
		for task in ${state}/${land}_Tasks/*_Tasks*.geojson; do
		    echo "    Processing MVUM task ${task}..."
		    num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		    ${dryrun} ogr2ogr -explodecollections -makevalid -clipsrc ${task} ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson ${state}/${land}_Tasks/mvum.geojson
		done
	    fi
    	done
    done
}

make_osm_extract() {
    # Make the data extract for the public land from OSM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    base="${1-yes}"
    tasks="${2-yes}"
    for state in ${states}; do
	echo "Extracting ${state} public lands from OSM..."
	for land in ${datasets["${state}"]}; do
	    # if test ! -e ${state}/${land}_Tasks; then
	    # 	mkdir -p ${state}/${land}_Tasks
	    # fi
	    if test x"${base}" == x"yes"; then
		echo "    Clipping OSM data for ${land}..."
		if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		    ${dryrun} osmium extract -s smart --overwrite --polygon ${boundaries}/NationalParks/${land}.geojson -o ${state}/${land}_Tasks/${land}_OSM_Highways.osm ${osmdata}
		else
		    ${dryrun} osmium extract -s smart --overwrite --polygon ${boundaries}/NationalForests/${land}.geojson -o ${state}/${land}_Tasks/${land}_OSM_Highways.osm ${osmdata}
		fi
	    fi

	    if test x"${tasks}" == x"yes"; then
		for task in ${state}/${land}_Tasks/*_Tasks*.geojson; do
		    echo "    Processing OSM task ${task}..."
		    num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		       ${dryrun} osmium extract -s smart --overwrite --polygon ${boundaries}/NationalParks/${land}.geojson -o ${state}/${land}_Tasks/${land}_OSM_Highways_${num}.osm ${state}/${land}_Tasks/${land}_OSM_Highways.osm
		    else
			${dryrun} osmium extract -s smart --overwrite --polygon ${boundaries}/NationalForests/${land}.geojson -o ${state}/${land}_Tasks/${land}_OSM_Highways_${num}.osm ${state}/${land}_Tasks/${land}_OSM_Highways.osm
		    fi
		done
	    fi
	    echo $task
	done
    done
}

make_baseset() {
    declare -A datasets
    datasets["Utah"]="${utah}"
    datasets["Colorado"]="${colorado}"
    datasets["Wyoming"]="${wyoming}"
  
    for base in ${states}; do
	echo "Processing ${base} public lands..."
	for land in ${datasets["${base}"]}; do
	    echo "    Making baseset for ${land}"
	    for file in ${source}; do
		rm -f ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson
		echo ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson /play/MapData/SourceData/Road_MVUM-out.geojson
		echo $file
	    done
	done
    done	
}

# process_forests() {
#     for forest in ${forests}; do
# 	if test "x${basesets}" = "xyes"; then
# 	    echo "    Making ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson"
# 	    rm -f ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson /play/MapData/SourceData/Road_MVUM-out.geojson

# 	    echo "    Making ${forest}_Tasks/${forest}_USFS_MVUM_Trails.geojson"
# 	    rm -f ${forest}_Tasks/${forest}_USFS_MVUM_Trails.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Trails.geojson /play/MapData/SourceData/Trail_MVUM-out.geojson

# 	    # Merge the MVUM roads and trails together, since in OSM they
# 	    # are both.
# 	    rm -f ${forest}_Tasks/${forest}_USFS_MVUM.geojson
# 	    ogrmerge.py -nln mvum -o ${forest}_Tasks/mvum.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Trails.geojson
# 	    ogrmerge.py -nln mvum -append -o ${forest}_Tasks/mvum.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson
	    
# 	    echo "    Making ${forest}_Tasks/${forest}_USFS_Trails.geojson"
# 	    rm -f ${forest}_Tasks/${forest}_USFS_Trails.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_Trails.geojson /play/MapData/SourceData/USFS_Trails-out.geojson

# 	    # echo "    Making ${forest}_Tasks/${forest}_USFS_MVUM.geojson"
# 	    # rm -f ${forest}_Tasks/${forest}_USFS_Trails.geojson
# 	    # ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM.geojson ${forest}.geojson ${forest}_Tasks/mvum.geojson 

# 	    echo "    Making ${forest}_Tasks/${forest}_USGS_Topo_Roads.geojson"
# 	    rm -f ${forest}_Tasks/${forest}_USGS_Topo_Roads.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USGS_Topo_Roads.geojson /play/MapData/SourceData/USGS_Topo_Roads-out.geojson

# 	    echo "    Making ${forest}_Tasks/${forest}_USGS_Topo_Trails.geojson"
# 	    rm -f ${forest}_Tasks/${forest}_USGS_Topo_Trails.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USGS_Topo_Trails.geojson /play/MapData/SourceData/USGS_Topo_Trails-out.geojson
# 	    osmium extract -s smart --overwrite --polygon ${forest}.geojson -o ${forest}_Tasks/${forest}_OSM_Roads.osm ../wy-co-ut.osm
# 	fi

# 	for task in ${forest}_Tasks/*Tasks_[0-9].geojson; do
#             base=$(echo ${task} | sed -e 's/Tasks_[0-9]*.geojson//')
#             num=$(echo ${task} | grep -o "Tasks_[0-9]*")
#             echo "    Processing task ${task}"
#             for dataset in ${source}; do
# 		echo "        Processing dataset ${dataset}..."
# 		new="${base}_${num}_${dataset}.geojson"
# 		rm -f ${new}
# 		if test ${dataset} == "OSM_Roads"; then
#                     osmium extract -s smart --overwrite --polygon ${task} -o ${base}_${num}_OSM_Roads.osm ${base}_${dataset}.osm
# 		elif test ${dataset} == "USFS_MVUM"; then
#                     ogr2ogr -explodecollections -clipsrc ${task} ${new} mvum.geojson
# 		else
#                     ogr2ogr -explodecollections -clipsrc ${task} ${new} ${base}_${dataset}.geojson
# 		fi
#             done
# 	done
#     done
# }

# process_parks() {
#     source="National_Park_Service Trails USGS_Topo_Trails"
#     for park in ${parks}; do
# 	echo "Processing national park ${park}, making base datasets..."
# 	if test "x${basesets}" = "xyes"; then
# 	    rm -f ${park}_Tasks/${park}_USGS_Topo_Trails-out.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${park}.geojson ${park}_Tasks/${park}_USGS_Topo_Trails.geojson /play/MapData/SourceData/USGS_Topo_Trails-out.geojson

# 	    rm -f ${park}_Tasks/${park}_NPS_Trails.geojson
# 	    ogr2ogr -explodecollections -makevalid -clipsrc ${park}.geojson ${park}_Tasks/${park}_NPS_Trails.geojson /play/MapData/SourceData/National_Park_Service_Trails-out.geojson

# 	    osmium extract -s smart --overwrite --polygon ${park}.geojson -o ${park}_Tasks/${park}_OSM_Trails.osm ../wy-co-ut.osm
# 	fi

# 	for task in ${park}_Tasks/*Tasks_[0-9].geojson; do
# 	    base=$(echo ${task} | sed -e 's/Tasks_[0-9]*.geojson//')
# 	    num=$(echo ${task} | grep -o "Tasks_[0-9]*")
# 	    echo "    Processing task ${task}"
# 	    for dataset in ${source}; do
# 		echo "        Processing dataset ${dataset}..."
# 		new="${base}_${num}_${dataset}.geojson"
# 		rm -f ${park}_Tasks/${park}_${num}_NPS_Trails.geojson
# 		ogr2ogr -explodecollections -makevalid -clipsrc ${park}.geojson ${park}_Tasks/${park}_${num}_NPS_Trails.geojson ${park}_Tasks/${park}_NPS_Trails.geojson

# 		rm -f ${park}_Tasks/${park}_${num}_USGS_Topo_Trails.geojson
# 		ogr2ogr -explodecollections -makevalid -clipsrc ${park}.geojson ${park}_Tasks/${park}_${num}_USGS_Topo_Trails.geojson ${park}_Tasks/${park}_USGS_Topo_Trails.geojson

# 		# osmium extract --no-progress --overwrite --polygon ${task} -o ${base}_${num}_OSM_Trails.osm ${base}_OSM_Trails.osm
# 		osmium extract -s smart --overwrite --polygon ${task} -o ${num}_OSM_Trails.osm ${base}_OSM_Trails.osm
# 		osmium tags-filter --overwrite -o ${base}_${num}_OSM_Trails.osm ${num}_OSM_Trails.osm w/highway=path
# 		# rm -f ${num}_OSM_Trails.osm
# 	    done
# 	done
#     done
# }

fixnames() {
    # Fix the OSM names
    osm=$(find -name \*.osm)
    for area in ${osm}; do
	${fixnames}h -v -i ${area}
    done
}

clean_tasks() {
    files=$(find -name \*_Tasks_[0-9]*.geojson)
    # echo ${files}
    rm -f ${files}
}

usage() {
    echo "This program builds all the smaller datasets from the"
    echo "larger source datasets."
    echo "--base (-b): build all base datasets, which is slow"
    echo "--parks (-p): Build only the National Parks"
    echo "--forests (-f): Build only the National Forests"
    echo "--datasets (-d): Build only this dataset for all boundaries"
    echo "--split (-s): Split the AOI into tasks, also very slow"
    echo "--extract (-e): Make a data extract from OSM"
    echo "--only (-o): Only process one state"
    echo "--tasks (-t): Split tasks boundaries into files for ogr2ogr"
    echo "--clean (-c): Remove generated task files"
}

if test $# -eq 0; then
    usage
    exit
fi

while test $# -gt 0; do
    case "$1" in
	-h|--help)
	    usage
	    exit 0
	    ;;
	-b|--base)
	    basesets="yes"
	    make_baseset
	    ;;
	-s|--split)
	    split_aoi
	    ;;
	-t|--tasks)
	    make_tasks
	    ;;
	-o|--only)
	    states=$1
	    ;;
	-p|--parks)
	    make_sub_tasks
	    # process_parks
	    ;;
	-f|--forests)
	    make_sub_mvum
	    # process_forests
	    ;;
	-d|--datasets)
	    basesets="no"
	    ;;
	-c|--clean)
	    clean_tasks
	    ;;
	-e|--extract)
	    make_osm_extract ${basesets} yes
	    make_mvum_extract ${basesets} yes
	    ;;
	-a|--all)
	    split_aoi
	    make_tasks
	    make_osm_extract ${basesets} yes
	    make_mvum_extract ${basesets} yes
	    ;;
	*)
	    # process_forests
	    # process_parks
	    ;;
    esac
    shift
done