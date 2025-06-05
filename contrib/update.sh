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
datasets["South_Dakota"]="${southdakota}"


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
    osmium tags-filter --overwrite -o us-highways.pbf $1 w/highway n/!=highway
}

get_path() {
    # Think of this like the Path class in python, but in bourne shell.
    inpath="${1:?}"

    declare -Ag path
    # The first part of the path is the state
    state=$(echo ${inpath} | cut -d '/' -f 1)
    # The second part is the region, park, forest. monument, or wilderness
    region=$(echo ${inpath} | cut -d '/' -f 2)
    path["state"]="${state}"
    path["region"]="${region}"
    path["short"]="$(echo ${region} | sed -e 's/_National.*//')"
    path["tasks"]="${path["short"]}_Tasks.geojson"
    # path["land"]="$(echo ${file} | cut -d '/' -f 2 | sed -e 's/_Task.*//')"
    # path["basename"]="$(basename ${file} | cut -d '.' -f 1)"
    # path["suffix"]="$(basename ${file} | cut -d '.' -f 2)"
    # path["task"]="$(echo ${file} | cut -d '/' -f 3)"
    # path["num"]="$(echo ${file} | grep -o "[0-9]*" | tail -1)"
    if test $(echo ${region} | grep -ci "Park") -gt 0; then
	path["type"]="park"
	path["aoi"]="NationalParks/${region}.geojson"
    fi
    if test $(echo ${region} | grep -ci "Monument") -gt 0; then
	path["type"]="monument"
	path["aoi"]="NationalMonuments/${region}.geojson"
    fi
    if test $(echo ${region} | grep -ci "Forest") -gt 0; then
	path["type"]="forest"
	path["aoi"]="NationalForests/${region}.geojson"
    fi
    if test $(echo ${region} | grep -ci "Wilderness") -gt 0; then
	path["type"]="wilderness"
	path["aoi"]="NationalWilderness/${region}.geojson"
    fi
    if test $(echo ${region} | grep -ci "Field Office") -gt 0; then
	path["type"]="blm"
	path["aoi"]="BLM/${region}.geojson"
    fi

    declare -p path

    return 0
}

make_extract() {
    # This clips the large datasets into small pieces, and supports both
    # OSM files and GeoJson. The input and output files are the same for
    # either format, it's only a few options that are different.
    clipsrc="${1:?}"

    get_path ${clipsrc}
    # if test $(echo ${intype} | grep -c "OSM") -eq 0; then
    # It's a GeoJson file
    #    indata="${path["dir"]}/${path["short"]}_${intype}"
    # fi
    if test x"${path["type"]}" == x"park"; then
	${tmsplitter} --extract ${npstrails} --infile ${boundaries}${path["aoi"]} --outfile ${path["state"]}/${path["region"]}/NPS_Trails.geojson
    fi
    if test x"${path["type"]}" == x"blm"; then
        ${tmsplitter} --extract ${blmhighways} --infile ${boundaries}${path["aoi"]} --outfile ${path["state"]}/${path["region"]}/BLM_Highways.geojson
    fi
    if test x"${path["type"]}" == x"forest"; then
	${tmsplitter} --extract ${mvumhighways} --infile ${boundaries}${path["aoi"]} --outfile ${path["state"]}/${path["region"]}/MVUM_Highways.geojson
	${tmsplitter} --extract ${usfstrails} --infile ${boundaries}${path["aoi"]} --outfile ${path["state"]}/${path["region"]}/USFS_Trails.geojson
    fi

    # Delete extracts for tasks with no data.
    empty=$(find ${path["state"]}/${path["region"]} -type f -size -170c)
    rm -f ${empty}

    return 0
}

split_aoi() {
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    get_path ${1}
    if test -d ${path["dir"]}; then
	echo "FOO"
    fi
    # dataset="${2:-all}"
    # for ${path["state"] in ${region}; do
    # 	if test ! -e ${state}; then
    # 	    mkdir ${state}
    # 	fi
    echo "Splitting ${state} into a task grid"
    # This generates a grid of roughly 5000sq km tasks,
    # which is the maximum TM supports. Some areas are
    # smaller than this, so only one polygon.
    # ${tmsplitter} --grid --infile ${aoi} --threshold 0.7 -o ${dir}/${short}_Tasks.geojson
    ${tmsplitter} --grid --infile ${boundaries}${path["aoi"]} -o ${path["state"]}/${path["region"]}/${path["tasks"]}
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
	    state=$1
	    ;;
	-s|--split)
	    split_aoi ${state}/${region}
	    break
	    ;;
	-d|--datasets)
	    shift
	    region=$1
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
	    split_aoi ${state}/${region}
	    make_extract ${state}/${region} # ${basedata}
	    break
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
