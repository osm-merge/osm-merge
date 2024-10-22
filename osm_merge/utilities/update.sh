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
boundaries="/play/MapData/Boundaries/"

# # The base datasets
# osmhighways="../wy-co-ut.osm.pbf"
# mvumhighways="../Road_MVUM-out.geojson"
# mvumtrails="../Trail_MVUM-out.geojson"
# topohighways="../USGS_Topo_Roads-out.geojson"
# topotrails="../USGS_Topo_Trails-out.geojson"
# npstrails="../National_Park_Service_Trails-out.geojson"
# usgstrails="../USFS_Trails-out.geojson"

utah="Dixie_National_Forest \
      Bryce_Canyon_National_Park \
      Zion_National_Park \
      Capitol_Reef_National_Park \
      Arches_National_Park \
      Manti_La_Sal_National_Forest \
      Canyonlands_National_Park \
      Uinta_Wasatch_Cache_National_Forest \
      Fishlake_National_Forest \
      Ashley_National_Forest"

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

# Debugging help
dryrun="" # echo

# The git branch, usually main except when debugging
branch="main"
root="${HOME}/projects/HOT/osm-merge.git"
# FIXME: gotta fix a dependency problem before these run from the
# shell script.
tmsplitter="${dryrun} ${root}/${branch}/osm_merge/utilities/tm-splitter.py"
osmhighway="${dryrun} ${root}/${branch}/osm_merge/utilities/osmhighways.py"

ogropts="${dryrun} ogr2ogr -t_srs EPSG:4326 -makevalid -explodecollections -clipsrc"
osmopts="${dryrun} osmium extract -s smart --overwrite --polygon "
osmconvert="${dryrun} osmconvert --complete-ways --drop-broken-refs -B="

get_path() {
    # Think of this like the Path class in python, but in bourne shell.
    file="${1:?}"
    # field="${2:?}"

    declare -Ag path
    path["state"]="$(echo ${file} | cut -d '/' -f 1)"
    path["land"]="$(echo ${file} | cut -d '/' -f 2 | sed -e 's/_Task.*//')"
    path["dir"]="${path["state"]}/${land}_Tasks"
    path["basename"]="$(basename ${file} | cut -d '.' -f 1)"
    path["suffix"]="$(basename ${file} | cut -d '.' -f 2)"
    path["short"]="$(echo ${land} | sed -e 's/_National_.*//')"
    # path["short"]="${path["dir"]}/$(echo ${land} | sed -e 's/_National_.*//')"
    path["task"]="$(echo ${file} | cut -d '/' -f 3)"
    path["num"]="$(echo ${file} | grep -o "[0-9]*")"

    declare -p path

    return 0
}

get_tasks() {
    # List the task files in a directory
    state="${1}"
    land="${2}"

    # Drop the category, the paths were getting too long.
    short=$(get_short_name ${land})
    tasks=$(ls ${state}/${land}_Tasks/${short}_Task_*.geojson)
    echo "${tasks}"

    return 0
}

get_subtasks() {
    # List the subtask files in a directory
    state="${1}"
    land="${2}"

    # Drop the category, the paths were getting too long.
    short=$(get_short_name ${land})
    subtasks=$(ls ${state}/${land}_Tasks/${short}_${num}/${land}_SubTask_*.geojson)
    echo "${subtasks}"

    return 0
}

get_task_num() {
    # Extract the task number from the file name.
    task="${1}"
    num=$(echo ${task} | grep -o "[0-9]*")
    if test x"${num}" = x; then
	# Top level forest or parks don't have a task number
	echo ""
    fi
    echo "Tasks_${num}"

    return 0
}

get_subtask_num() {
    # Extract the 2 task numbers from the file name.
    task="${1:?}"
    nums=$(echo ${task} | grep -o "[0-9]*[0-9]*" | tr '\n' '_')
    length=$(expr $(echo ${#nums} - 1))
    if test ${length} -lt 0; then
       echo ""
    else
	subnum="${nums:0:${length}}"
	echo "SubTask_${subnum}"
    fi

    return 0
}

get_dirname() {
    # Extract the directory name from the filename.
    file="${1:?}"
    dir=$(echo ${file} | cut -d '.' -f 1)
    echo ${dir}

    return 0
}

get_short_name() {
    # Drop the National_Forest or National_Park part of the path
    name="${1:?}"
    short=$(basename ${name} | sed -e "s/_National_Forest//" -e "s/National_Park//" -e "s/Tasks/Task/")
    echo ${short}

    return 0
}

extract_data() {
    # This clips the large datasets into small pirces, and support both
    # OSM files and GeoJson. The input and output files are the same for
    # either format, it's only a few options that are different.
    clipsrc="${1:?}"
    intype="${2:?}"
    subtask="${3:-no}"

    # Use an absolute path to avoid problems with whichever
    # directory we are executing code in.
    sources="/play/MapData/SourceData"
    mvumtrails="${sources}/Trail_MVUM-out.geojson"
    topotrails="${sources}/USGS_Topo_Trails-out.geojson"
    usgstrails=

    declare -Ag data
    data["OSM_Highways"]="${sources}/wy-co-ut.osm.pbf"
    data["MVUM_Highways"]="${sources}/Road_MVUM-out.geojson"
    data["MVUM_Trails"]="${sources}/Trail_MVUM-out.geojson"
    data["USGS_Highways"]="${sources}/USGS_Topo_Roads-out.geojson"
    data["NPS_Trails"]="${sources}/National_Park_Service_Trails-out.geojson"
    # data["OSM_Trails"]=
    # data["USGS_Trails"]="${sources}/USFS_Trails-out.geojson"

    for task in ${clipsrc}; do
	echo "    Extracting data from ${dataset} task ${task} ..."
	get_path ${task}
	if test x"${path["num"]}" = x; then
	    echo "Top level forest or park"
	fi
	if test x"${subtask}" = x"yes"; then
	    outfile="${path["dir"]}/${intype}_Task_${path["num"]}"
	else
	    outfile="${path["dir"]}/${intype}_Task_${path["num"]}"
	fi
	declare -p path

	indata="${path["dir"]}/${path["short"]}_${intype}.osm"
	if test $(echo ${intype} | grep -c "OSM") -eq 0; then
	    # It's a GeoJson file
	    ${ogropts} -nlt LINESTRING ${task} ${outfile}.geojson ${indata}
	else
	    # It's an OSM XML file
	    # ${osmhighway} --clip ${task} -v -o ${outfile}.osm -i ${indata}
	    # ${osmopts} ${task} -o ${outfile}.osm ${indata}
	    ${osmconvert}${task} ${indata} > ${outfile}.osm 
	fi

    done

    return 0
}

split_aoi() {
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    tmmax=70000
    for state in ${region}; do
	echo "Splitting ${state} into squares with ${tmmax} per side"
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    short=$(get_short_name ${base})
	    echo "    Making TM sized projects for ${land}"
	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		aoi="${boundaries}/NationalParks/${land}.geojson"
	    else
		aoi="${boundaries}/NationalForests/${land}.geojson"
	    fi
	    # This generates a grid of roughly 5000sq km tasks,
	    # which is the maximum TM supports. Some areas are
	    # smaller than this, so only one polygon.
	    # ${tmsplitter} --grid --infile ${aoi} --threshold 0.7 -o ${dir}/${short}_Tasks.geojson
	    ${tmsplitter} --grid --infile ${aoi} --threshold 0.7 -o ${dir}/${short}.geojson
	    # Make a multipolygon even if just one task
	    # ${ogropts} ${aoi} ${dir}/${short}_Tasks.geojson output.geojson
	    # rm -f output.geojson
	    echo "Wrote ${base}_Tasks.geojson"
	done
    done
}

make_tasks() {
    # Split the multipolygon from tm-splitter into indivigual files
    # for ogr2ogr and osmium.
    # $1 is an optional state to be the only one processed
    # $2 is an optional national forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    for state in ${region}; do
	echo "Making task boundaries for for ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    for task in ${state}/${land}_Tasks/*Task*.geojson; do
		get_path ${task}
		echo "    Making task boundaries for clipping to ${land}"
		${tmsplitter} -v -s -i ${task} -o ${path["dir"]}/${path["short"]}
		tasks=${dir}/${short}Task_*.geojson
	     	echo "Wrote tasks for ${task} ..."
	    done
	done
    done
}

make_sub_tasks() {
    # Split the polygon of the task into smaller sizes, each to fit
    # a small TM task. These are used to make small task sized
    # data extracts of the post conflated data to avoid lots of
    # cut & paste.
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:all}"
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    for task in $(get_tasks ${state} ${land}); do
		get_path ${task}
  		echo "    Making task boundaries for clipping to ${path["land"]}"
		base="${path["dir"]}/${path["basename"]}"
		if test ! -e ${base}; then
		    mkdir -p ${base}
		fi
		# echo "    Making sub task boundaries for ${task}"
		${tmsplitter} --grid --infile ${task} --threshold 0.1
		# Clip to the boundary
		${ogropts} -nlt POLYGON ${task} ${path["dir"]}/${path["short"]}_SubTask_${path["num"]}.geojson output.geojson
		outfile=${base}/${path["short"]}_${path["num"]}
		${tmsplitter} -v --split --infile ${path["dir"]}/${path["short"]}_Task_${path["num"]}.geojson -o ${outfile}
	    done
	done
    done
}

make_sub_mvum() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional national forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"    
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    short=$(basename ${land} | sed -e "s/_National_Forest//" -e "s/National_Park//")
	    extract_data "${state}/${land}_Tasks/${short}_Task_*/*.geojson" MVUM_Highways yes
	done
    done
}

make_sub_osm() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"    
    # Make the data extract for the public land from OSM
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    short=$(basename ${land} | sed -e "s/_National_Forest//" -e "s/National_Park//")
	    extract_data "${state}/${land}_Tasks/${short}_Task_*/*.geojson" OSM_Highways yes
	done
    done
}

make_nps_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    base="${1-yes}"
    tasks="${2-yes}"
    basedata="no" # this makes the base dataset for the forest or park

    # Make the data extract from the NPS Trail data
    for state in ${states}; do
     	echo "Processing NPS data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test $(echo ${land} | grep -c "_Forest" ) -gt 0; then
		continue
	    fi
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    if test x"${basedata}" == x"yes"; then
		echo "    Making ${land}_NPS_Trails.geojson"
		rm -f ${state}/${land}_Tasks/${land}_NPS_Trails.geojson
		${ogropts} -nlt LINESTRING ${boundaries}/NationalParks/${land}.geojson ${state}/${land}_Tasks/${land}_NPS_Trails.geojson ${npstrails}
	    fi
	    dir="${state}/${land}_Tasks"
	    extract_data "${dir}/${land}_Tasks_*.geojson" NPS_Trails
    	done
    done
}

make_topo_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    region="${1:-${states}}"
    dataset="${2:-all}"
    # base=${3:-no}
    basedata="no" # this makes the base dataset for the forest or park
    for state in ${states}; do
     	echo "Processing Topo data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    else
		clip="NationalForests"
	    fi
	    if test x"${basedata}" == x"yes"; then
		echo "    Making ${land}_NPS_Trails.geojson"
		rm -f ${forest}_Tasks/${land}_Topo_Trails.geojson
		# ${ogropts} -nlt LINESTRING -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson ${topotrails}
		${tmsplitter} -v -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson -i ${topotrails}

		rm -f ${forest}_Tasks/${land}_Topo_Trails.geojson
		# ${ogropts} -nlt LINESTRING -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_USGS_Topo_Trails.geojson ${topohighways}
		${tmsplitter} -v -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_USGS_Topo_Trails.geojson -i ${topohighways}
	    fi

	    dir="${state}/${land}_Tasks"
	    extract_data "${dir}/*_Tasks_*.geojson" USGS_Topo
    	done
    done
}

make_sub_nps() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"    
    # Make the data extract for the public land from OSM
    for state in ${region}; do
	for land in ${datasets["${state}"]}; do
	    if test $(echo ${land} | grep -c "_Forest" ) -gt 0; then
		continue
	    fi
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
		continue
	    fi
	    echo "Processing public lands in ${state}..."
	    short=$(get_short_name ${land})
	    extract_data "${state}/${land}_Tasks/${land}_Tasks_*/*.geojson" NPS_Trails yes
	done
    done
}

make_sub_topo() {
    echo "make_sub_topo() unimplemented"
}

make_mvum_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    # base=${3:-no}
    baseset="no"
    # tasks=${4:-no}
    tasks="yes"

    for state in ${region}; do
     	echo "Processing MVUM data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    tasks=$(get_tasks ${state} ${land})
	    echo $tasks
	    for i in ${tasks}; do
		subtasks=$(get_subtasks ${state} ${land} ${i})
		echo $subtasks
	    done

	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    else
		clip="NationalForests"

	    fi
	    if test x"${baseset}" == x"yes"; then
		rm -f ${state}/${land}_Tasks/${land}_MVUM_Highways.geojson
		echo "    Making ${land}_MVUM_Highways.geojson"
		${ogropts} -nlt LINESTRING ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Highways.geojson ${mvumhighways}
		# ${tmsplitter} -v -complete -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_MVUM_Highways.geojson -i ${mvumhighways}

		# echo "    Making ${land}_MVUM_Trails.geojson"
		# rm -f ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson
		# ${ogropts} -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson ${mvumtrails}
		# ${tmsplitter} -v -complete -e ${boundaries}/${clip}/${land}.geojson -i ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson -i ${mvumtrails}

		# Merge the MVUM roads and trails together, since in OSM they
		# are both in the data extract used for vconflation.
		# echo "    Merging MVUM Trails and Roads together"
		# rm -f ${state}/${land}_Tasks/mvum.geojson
		# ${dryrun} ogrmerge.py -nln mvum -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
		# ${dryrun} ogrmerge.py -nln mvum -append -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
	    fi

	    dir="${state}/${land}_Tasks"
	    extract_data "${dir}/*_Task_*.geojson" MVUM_Highways
    	done
    done
}

make_osm_extract() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    basedata="yes" # this makes the base dataset for the forest or park

    # Clipping is not done on state boundaries since National Forests often
    # cross state lines.
    for state in ${region}; do
	echo "Extracting ${state} public lands from OSM..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    # get_path ${task}
	    # if test ! -e ${base}_Tasks; then
	    # 	mkdir -p ${state}/${land}_Tasks
	    # fi
	    if test x"${basedata}" == x"yes"; then
		short=$(get_short_name ${land})
		# echo "    Clipping OSM data for ${land}..."
		if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		    ${osmhighways} -v --clip ${boundaries}/NationalParks/${land}.geojson -o ${state}/${short}_OSM_Highways.osm -i ${osmdata}
		    # ${osmopts} --polygon ${boundaries}/NationalParks/${land}.geojson -o ${state}/${short}_OSM_Highways.osm ${osmdata}
		else
		    ${osmhighways} -v --clip ${boundaries}/NationalForests/${land}.geojson -o ${state}/${land}_Tasks/${short}_OSM_Highways.osm -i ${osmdata}
		    # ${osmopts} --polygon ${boundaries}/NationalForests/${land}.geojson -o ${base}_OSM_Highways.osm  ${osmdata}
		fi
		# Fix the names & refs in the OSM data
		# ${dryrun} ${fixnames} -v -i ${base}_OSM_Highways.osm
		# ${dryrun} mv out-out.osm ${base}_OSM_Highways.osm
	    fi

	    # tasks=${base}*_Tasks_*.geojson
	    extract_data "${state}/${land}_Tasks/*_Task_[0-9]*.geojson" OSM_Highways
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
		echo ${ogropts} -nlt LINESTRING -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson /play/MapData/SourceData/Road_MVUM-out.geojson
		echo $file
	    done
	done
    done	
}

fixnames() {
    # Fix the OSM names
    osm=$(find -name \*.osm)
    for area in ${osm}; do
	${fixnames} -v -i ${area}
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
    echo "--tasks (-t): Split tasks boundaries into files for ogr2ogr"
    echo "--base (-b): build all base datasets, which is slow"
    echo "--forests (-f): Build only the National Forests"
    echo "--datasets (-d): Build only this dataset for all boundaries"
    echo "--split (-s): Split the AOI into tasks, also very slow"
    echo "--extract (-e): Make a data extract from OSM"
    echo "--only (-o): Only process one state"
    echo "--dryrun (-n): Don't actually write any datafiles"
    echo "--clean (-c): Remove generated task files"
}

if test $# -eq 0; then
    usage
    exit
fi

# To speciofy a single state and/or forest or park, the -o and -d
# options must be before the actions.
while test $# -gt 0; do
    case "$1" in
	-h|--help)
	    usage
	    exit 0
	    ;;
	-n|--dryrun)
	    dryrun="echo"
	    ;;
	-b|--base)
	    basedata="yes"
	    # make_baseset
	    break
	    ;;
	-o|--only)
	    shift
	    region=$1
	    ;;
	-s|--split)
	    split_aoi ${region} ${dataset}
	    break
	    ;;
	-d|--datasets)
	    shift
	    dataset=$1
	    ;;
	-t|--tasks)
	    make_tasks ${region} ${dataset}
	    make_sub_tasks ${region} ${dataset}
	    break
	    ;;
	-f|--forests)
	    make_sub_mvum
	    break
	    # process_forests
	    ;;
	-c|--clean)
	    clean_tasks
	    break
	    ;;
	-e|--extract)
	    # This may run for a long time.
	    make_osm_extract ${region} ${dataset} ${basedata}
	    # make_sub_osm ${region} ${dataset} ${basedata}
	    # make_mvum_extract ${region} ${dataset} ${basedata}
	    # make_sub_mvum ${region} ${dataset}
	    # make_nps_extract ${region} ${dataset} ${basedata}
	    # make_sub_nps ${region} ${dataset} ${basedata}
	    # make_topo_extract ${region} ${dataset} ${basedata}
	    # make_sub_topo ${region} ${dataset} ${basedata}
	    break
	    ;;
	-a|--all)
	    # The kitchen sink, do everything
	    split_aoi
	    make_tasks
	    make_sub_tasks
	    make_osm_extract ${basesets} yes
	    make_sub_osm ${basesets} yes
	    make_mvum_extract ${basesets} yes
	    make_sub_mvum
	    make_nps_extract
	    make_sub_nps
	    make_topo_extract
	    make_sub_topo
	    break
	    ;;
	-w)
	    # FIXME: this is just for testing
	    shift
	    eval $(get_path $1 state)
	    echo "FOO: ${components["num"]}"
	    ;;
	*)
	    usage
	    ;;
    esac
    shift
done