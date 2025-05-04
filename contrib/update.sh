#!/bin/bash

# Copyright (C) 2024, 2025 OpenStreetMap US
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
# for every task being setup for the HOT Tasking Manager. Most people
# would have probably written this in python, but since most of this
# is executing external command line utilities, Bourne shell works better.

states="Utah Colorado Wyoming"
# Louisiana New_Mexico South_Dakota Arkansaw Oklahoma New_York Virginia Michigan Maine Minnesota .git Oregon North_Carolina Illinois North_Dakota Utah Wyoming Arizona West_Virginia Nebraska California Tennesse Nevada Idaho Washington Vermont Puerto_Rico Indiana Kentucky Pennsylvania Alaska Colorado Georgia Montana New_Hampshire Ohio South_Carolina Missouri"

# This is a more complete list of national forests and parks, but aren't
# included due to lack of disk space. Someday...
source states.sh

# Top level for boundaries, allow to set via env variable
if test x"${BOUNDARIES}" = x; then
    boundaries="/work/Boundaries/"
else
    boundaries="${BOUNDARIES}"
fi

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
          Medicine_Bow_Routt_National_Forests \
          Grand_Mesa_Uncompahgre_and_Gunnison_National_Forests \
          Rio_Grande_National_Forest \
          San_Juan_National_Forest \
	  White_River_National_Forest \
	  Pike_and_San_Isabel_National_Forests \
          Rocky_Mountain_National_Park \
	  Great_Sand_Dunes_National_Park \
	  Mesa_Verde_National_Park \
	  Black_Canyon_of_the_Gunnison_National_Park \
	  Kremmling_Field_Office \
	  Dillon_Field_Office \
	  Grand_Junction_Field_Office \
	  San_Luis_Valley_Field_Office \
	  Little_Snake_Field_Office \
	  Colorado_River_Valley_Field_Office \
	  Uncompahgre_Field_Office \
	  Gunnison_Field_Office"

wyoming="Bighorn_National_Forest \
         Bridger_Teton_National_Forest \
         Ashley_National_Forest \
         Caribou_Targhee_National_Forest \
         Shoshone_National_Forest \
         Black_Hills_National_Forest \
         Yellowstone_National_Park \
         Grand_Teton_National_Park"

# Use an absolute path to avoid problems with whichever
# directory we are executing code in.
if test x"${SOURCEDATA}" = x; then
    sources="/work/SourceData"
else
    sources="${SOURCEDATA}"
fi

# USDS Datasets
osmdata="${sources}/us-highways.pbf"
# osmdata="${sources}/wy-co-ut-highways.pbf"
mvumtrails="${sources}/Trail_MVUM-out.geojson"
mvumhighways="${sources}/Road_MVUM-out.geojson"
roadcore="${sources}/RoadCore-out.geojson"
npstrails="${sources}/National_Park_Service_Trails-out.geojson"
topotrails="${sources}/USGS_Topo_Trails-out.geojson"
usfstrails="${sources}/USFS_Trails-out.geojson"

# BLM Datasets
blmroads="${sources}/BLM_Public_Motorized_Roads.geojson"
blmtrails="${sources}/BLM_Public_Motorized_Trails.geojson"
blmrec="${sources}/BLM_National_Recreation_Site_Points.geojson"

# These are state only files
# Colorado, which is my focus since I live here.
coroads="${sources}/Tasks/Colorado/Colorado_Roads-out.geojson"
coblm="${sources}/Tasks/Colorado/BLM_Colorado_Routes_by_Allowed_Mode_of_Transportation-out.geojson"

# These are the states I'm focused on
declare -gA datasets
datasets["Utah"]="${utah}"
datasets["Colorado"]="${colorado}"
datasets["Wyoming"]="${wyoming}"
datasets["BLM"]="${blmroads} ${blmtrails}"
datasets["Roads"]="${coroads}"
datasets["New_Mexico"]="${newmexico}"
# datasets["South_Dakota"]="${southdakota}"

# The rest of the country
datasets["Washington"]="${washington}"
# datasets["Nevada"]="${nevada}"
# datasets["Arizona"]="${arizona}"
# datasets["Idaho"]="${idaho}"
# datasets["Oregon"]="${oregon}"
# datasets["California"]="${california}"
# datasets["Montana"]="${montana}"
# datasets["North_Dakota"]="${northdakota}"
# datasets["Tennesse"]="${tennessee}"
# datasets["North_Carolina"]="${northcarolina}"
# datasets["South_Carolina"]="${southcarolina}"
# datasets["Wisconson"]="${wisconson}"
# datasets["Puerto_Rico"]="${puertorico}"
# datasets["Alaska"]="${alaska}"
# datasets["Arkansaw"]="${arkansaw}"
# datasets["Georgia"]="${georgia}"
# datasets["Illinois"]="${illinois}"
# datasets["Indiana"]="${indiana}"
# datasets["Kentucky"]="${kentucky}"
# datasets["Louisiana"]="${louisiana}"
# datasets["Maine"]="${Maine}"
# datasets["Michigan"]="${michigan}"
# datasets["Minnesota"]="${minnesota}"
# datasets["Missouri"]="${missouri}"
# datasets["Nebraska"]="${nebraska}"
# datasets["New_Hampshire"]="${newhampshire}"
# datasets["New_York"]="${newyork}"
# datasets["Ohio"]="${ohio}"
# datasets["Oklahoma"]="${oklahoma}"
# datasets["Pennsylvania"]="${pennsylvania}"
# datasets["Vermont"]="${vermont}"
# datasets["West_Virginia"]="${westvirginia}"
# datasets["Virginia"]="${virginia}"

# Debugging help
dryrun="" # echo

# if test x"${UTILITIES}" = x; then
#     root="${HOME}/projects/OSM-US/osm-merge.git"
# else
#     root="${UTILITIES}"
# fi
geo2poly="${dryrun} geojson2poly"
tmsplitter="${dryrun} tm-splitter -v"
osmhighways="${dryrun} osmhighways -v"

# Note that the option for the boundary to clip with is in this list,
# so when invoking these variables, the boundary must be first.
ogropts="${dryrun} ogr2ogr -progress -t_srs EPSG:4326 -makevalid -explodecollections -clipsrc"
osmopts="${dryrun} osmium extract -s smart --overwrite --polygon "
osmconvert="${dryrun} osmconvert --drop-broken-refs "

convert_zips() {
    for zip in ${sources}/*.zip; do
	new="$(echo ${zip} | cut -d '.' -f 2 | sed -e 's/_FS//')"
	if test x"${new}" == x"TrailNFS_Publish"; then
	    new="NFS_Trail"
	fi
	if test $(echo ${zip} | grep -c BLM) -gt 0; then
	    new="$(echo ${zip} | cut -d '.' -f 1)"
	fi
	echo "Converting ZIP from NAD 83 to GeoJson NAD84: ${new}.geojson"
	${dryrun} ogr2ogr -progress -t_srs EPSG:4326 -s_srs EPSG:4269  -makevalid -explodecollections ${sources}/${new}.geojson ${zip}
    done
}

osm_highways() {
    osmium tags-filter --overwrite -o us-highways.pbf $1 w/highway
}

get_path() {
    # Think of this like the Path class in python, but in bourne shell.
7    file="${1:?}"
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
    path["num"]="$(echo ${file} | grep -o "[0-9]*" | tail -1)"

    declare -p path

    return 0
}

get_tasks() {
    # List the task files in a directory
    state="${1}"
    land="${2}"

    # Drop the category, the paths were getting too long.
    short=$(get_short_name ${land})
    tasks=$(ls ${state}/${land}_Tasks/${short}_Tasks*.geojson)
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
    short=$(basename ${name} | sed -e "s/_National.*//" -e "s/Tasks/Task/")
    echo ${short}

    return 0
}

extract_data() {
    # This clips the large datasets into small pieces, and supports both
    # OSM files and GeoJson. The input and output files are the same for
    # either format, it's only a few options that are different.
    clipsrc="${1:?}"
    intype="${2:?}"
    subtask="${3:-no}"

    # get_path ${}
    # if test $(echo ${intype} | grep -c "OSM") -eq 0; then
    # It's a GeoJson file
    #    indata="${path["dir"]}/${path["short"]}_${intype}"
    # fi
    ${tmsplitter} -v -e ${mvumhighways} -i ${boundaries}/${clip}/${short}_Tasks.geojson

    return 0
}

split_aoi() {
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    for state in ${region}; do
	if test ! -e ${state}; then
	    mkdir ${state}
	fi
	echo "Splitting ${state} into squares with ${tmmax} per side"
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    short=$(get_short_name ${land})
	    echo "    Making TM sized projects for ${land}"
	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		aoi="${boundaries}/NationalParks/${land}.geojson"
	    elif test $(echo ${land} | grep -c "_Office" ) -gt 0; then
		aoi="${boundaries}/BLM/${land}.geojson"
	    else
		aoi="${boundaries}/NationalForests/${land}.geojson"
	    fi
	    if test ! -e ${dir}; then
		mkdir ${dir}
	    fi
	    # This generates a grid of roughly 5000sq km tasks,
	    # which is the maximum TM supports. Some areas are
	    # smaller than this, so only one polygon.
	    # ${tmsplitter} --grid --infile ${aoi} --threshold 0.7 -o ${dir}/${short}_Tasks.geojson
	    ${tmsplitter} -v --grid --infile ${aoi} -o ${dir}/${short}_Tasks.geojson
	    echo "Wrote task ${dir}/${short}_Tasks.geojson"
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
	    short="$(get_short_name ${land})"
	    for task in ${state}/${land}_Tasks/${short}_Tasks.geojson; do
		get_path ${task}
		echo "    Making task boundaries for clipping to ${land}"
		${tmsplitter} -v -s -i ${task} -o ${path["dir"]}/${path["short"]}_Task
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
		# ${tmsplitter} --grid --infile ${task} --threshold 0.1
		# Clip to the boundary
		indata="${path["dir"]}/${path["short"]}_SubTasks_${path["num"]}.geojson"
		outfile=${base}/${path["short"]}_Sub
		${tmsplitter} -v --split --infile ${indata} -o ${outfile}
		rm -f ${indata}
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
	    if test $(echo ${land} | grep -c Park) -gt 0; then
		continue
	    fi
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    short="$(get_short_name ${land})"
	    infiles="${state}/${land}_Tasks/${short}_Task_*/*.geojson"
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
	    short="$(get_short_name ${land})"
	    infiles="${state}/${land}_Tasks/${short}_Task_*/*.geojson"
	    extract_data "${infiles}" OSM_Highways yes
	done
    done
}

make_nps_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    # base=${3:-no}
    baseset="yes"
    # tasks=${4:-no}
    tasks="yes"

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
	    if test x"${baseset}" == x"yes"; then
		echo "    Making ${land}_NPS_Trails.geojson"
		rm -f ${state}/${land}_Tasks/${land}_NPS_Trails.geojson
		short="$(get_short_name ${land})"
		${ogropts} ${boundaries}/NationalParks/${land}.geojson  -nlt LINESTRING ${state}/${land}_Tasks/${short}_NPS_Trails.geojson ${npstrails}
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
	    short="$(get_short_name ${land})"
	    infiles="${state}/${land}_Tasks/${short}_Task_*/*.geojson"
	    extract_data "${infiles}" NPS_Trails yes
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
    baseset="yes"
    # tasks=${4:-no}
    tasks="yes"

    for state in ${region}; do
     	echo "Processing MVUM data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test $(echo ${land} | grep -c Park) -gt 0; then
		continue
	    fi
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    elif test $(echo ${land} | grep -c "_Office" ) -gt 0; then
		clip="BLM"
	    else
		clip="NationalForests"

	    fi
	    outdata="${state}/${land}_Tasks/${land}_MVUM_Highways.geojson"
	    if test ! -e ${outdata}; then
	    	# rm -f ${outdata}
		short=$(get_short_name ${land})
		if test $(echo ${land} | grep -c "_Office" ) -gt 0; then
		    echo "    Making ${short}_BLM_Roads.geojson ..."
		    ${ogropts} ${boundaries}/${clip}/${land}.geojson -nlt LINESTRING ${state}/${land}_Tasks/${short}_BLM_Roads.geojson ${blmroads}
		else
		    echo "    Making ${short}_MVUM_Highways.geojson ..."
		    # ${ogropts} ${boundaries}/${clip}/${land}.geojson -nlt LINESTRING ${state}/${land}_Tasks/${short}_MVUM_Highways.geojson ${mvumhighways}
		    ${tmsplitter} -e ${mvumhighways} -i ${state}/${land}_Tasks/${short}_Tasks.geojson -o ${state}/${land}_Tasks/${short}.geojson
 		fi
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
	    if test $(echo ${land} | grep -c "_Office" ) -gt 0; then
		extract_data "${dir}/*_Task_*.geojson" BLM_Roads
	    else
		extract_data "${dir}/*_Task_*.geojson" MVUM_Highways
	    fi
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
    baseset="yes" # this makes the base dataset for the forest or park

    # Clipping is not done on state boundaries since National Forests often
    # cross state lines.
    for state in ${region}; do
	echo "Extracting ${state} public lands from OSM..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    if test x"${baseset}" == x"yes"; then
		short=$(get_short_name ${land})
		# echo "    Clipping OSM data for ${land}..."
		if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		    # There's 3 ways to clip an OSM XML file
		    ${osmopts} ${boundaries}/NationalParks/${land}.geojson -o ${state}/${short}_OSM_Highways.osm ${osmdata}
		    continue
		elif test $(echo ${land} | grep -c "_Office" ) -gt 0; then
		    base="${state}/${land}_Tasks/${short}"
		    ${osmopts} ${boundaries}/BLM/${land}.geojson -o ${base}_OSM_Highways.osm ${osmdata}
		else
		    # ${osmhighway} ${boundaries}/NationalForests/${land}.geojson -o ${state}/${land}_Tasks/${short}_OSM_Highways.osm -i ${osmdata}
		    base="${state}/${land}_Tasks/${short}"
		    ${osmopts} ${boundaries}/NationalForests/${land}.poly -o ${base}_OSM_Highways.osm ${osmdata}
		    # ${osmconvert} -B=${boundaries}/NationalForests/${land}.poly ${osmdata} -o=${state}/${land}_Tasks/${short}_OSM_Highways.osm
		fi
		# Fix the names & refs in the OSM data
		# ${dryrun} ${fixnames} -v -i ${base}_OSM_Highways.osm
		# ${dryrun} mv out-out.osm ${base}_OSM_Highways.osm
	    fi

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
    echo "--filter (-f): Filter highways only from the OSM data"
    echo "--datasets (-d): Build only this dataset for all boundaries"
    echo "--split (-s): Split the AOI into tasks, also very slow"
    echo "--extract (-e): Make a data extract from OSM"
    echo "--only (-o): Only process one state"
    echo "--dryrun (-n): Don't actually write any datafiles"
    echo "--clean (-c): Remove generated task files"
    echo "--update (-u): Update intitial conversion from official sources"
}

if test $# -eq 0; then
    usage
    exit
fi

# To specify a single state and/or forest or park, the -o and -d
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
	    # make_sub_tasks ${region} ${dataset}
	    break
	    ;;
	-f|--filter)
	    shift
	    osm_highways $1
	    # make_sub_mvum
	    break
	    # process_forests
	    ;;
	-c|--clean)
	    clean_tasks
	    break
	    ;;
	-e|--extract)
	    # This may run for a long time.
	    # make_osm_extract ${region} ${dataset} ${basedata}
	    # make_sub_osm ${region} ${dataset} ${basedata}
	    make_mvum_extract ${region} ${dataset} ${basedata}
	    # make_sub_mvum ${region} ${dataset}
	    # make_nps_extract ${region} ${dataset} ${basedata}
	    # make_sub_nps ${region} ${dataset} ${basedata}
	    # make_topo_extract ${region} ${dataset} ${basedata}
	    # make_sub_topo ${region} ${dataset} ${basedata}
	    break
	    ;;
	-a|--all)
	    # The kitchen sink, do everything
	    split_aoi ${region} ${dataset}
	    make_tasks ${region} ${dataset}
	    make_sub_tasks ${region} ${dataset}
	    make_osm_extract ${region} ${dataset} ${basedata}
	    make_mvum_extract ${region} ${dataset} ${basedata}
	    make_nps_extract ${region} ${dataset} ${basedata}
	    exit
	    ;;
	-u)
	    convert_zips
	    ;;
	*)
	    usage
	    ;;
    esac
    shift
done

# Cleanup temp files
rm -f osmconvert_tempfile*
