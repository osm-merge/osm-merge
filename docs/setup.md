
This is more focused on the backend of the website that makes all the
processed data available. Or other crazy people who have a need to
work on much larger areas. The output datasets this will generate a
lot of files if you plan to work with multiple national forests or
parks. I use a tree structure. At the top is the directory with all
the source files. You also need a directory with the national forest
or park boundaries which get used for data clipping.

Once I have the source files ready, I start the splitting up process
to make data extracts for each forest or park. If you are only working
on one forest or park, you can do this manually. Since I'm working
with data for multiple states, I wrote a shell script to automate the
process. For OSM, you need to either merge multiple state level data
into a single file, or use the very large US dataset.

Since this project is focused on remote highways and trails, for the
source OSM dataset I use a subset of the entire US, a data extract of
only highways. This will get clipped by the boundary of each area when
updating source datasets.

## Boundaries

You need boundaries with a good geometry. These can be extracted from
OpenStreetMap, they're usually relations. The official boundaries are
also available from the same site as the datasets as a
MultiPolygon. This file contains boundaries for the entire US, so to
use other tools like [ogr2ogr](https://gdal.org/programs/ogr2ogr.html)
or [osmium](https://osmcode.org/osmium-tool/), it needs to be split
into separate files.

I use the [TM Splitter](tm-splitter.md) utility included in this project
to split the MultiPolygon into these separate files, one for each
public land area. Each of these files are also a MultiPolygon, since
often a national forest or park has several areas that aren't
connected.

## update.sh

Most of the process is executing other external programs like
[osmium](https://osmcode.org/osmium-tool/) or
[ogr2ogr](https://gdal.org/programs/ogr2ogr.html), so I wrote a bourne
shell script to handle all the repetitious tasks. This also lets me
easily regenerate all the files if I make a change to any of the
utilities or the process. This uses a modern shell syntax with
functions and data structures to reduce cut & paste.

The command line options this program supports are:

	--tasks (-t): Split tasks boundaries into files for ogr2ogr
	--datasets (-d): Build only this dataset for all boundaries
	--split (-s): Split the AOI into tasks, also very slow
	--extract (-e): Make a data extract from OSM
	--only (-o): Only process one state
	--dry run (-n): Don't actually write any datafiles
	--base (-b): build all base datasets, which is slow
	
The locations of the files is configurable, so it can easily be
extended for other forests or parks. This script is in the
[cont rib](https://github.com/osm-merge/osm-merge/blob/main/contrib/update.sh)
directory of this project.

This also assumes you want to build a tree of output directories.

For example I use this layout:

	SourceData
		-> Tasks
			-> Colorado
				-> Medicine_Bow_Rout_National_Forest_Tasks
					-> Medicine_Bow_Rout_Task_[task number]
				-> Rocky_Mountain_National_Park_Task
					-> Rocky_Mountain_National_Park_Task_[task number]
	        -> Utah
				-> Bryce_Canyon_National_Park_Tasks
			etc...
			
All my source datasets are in __SourceData__.   In the __Tasks__
directory I have all the Multi Polygon files for each forest or park. I
create these files by running *update.sh --split*. These are the large
files that have the AOI split into 5000km sq polygons.

Since I'm working with multiple states, that's the next level, and
only contains the sub directories for all the forests or parks in that
state. Note that some national forests cross state boundaries. This
does not effect task splitting, as that's done using the boundary of
the entire forest. It does effect making the OSM data extract if you
are using data downloaded from GeoFabrik, since they are usually done
on a per state basis. The source data extract needs to cover
multiple states, or the entire US. Multiple state data files
can be merged using
[ogrmerge](https://gdal.org/en/latest/programs/ogrmerge.html).

While there is support for all the states, right now it's focused on
Colorado, Utah, and Wyoming. I use these for debugging the data
splitting and conversion processes, and to prepare the data extracts
for conflation. The other states can be reactivated by uncommenting
them in the shell script.
