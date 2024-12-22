# Mapper Data flow

Much of the process of conflation is preparing the datasets since
we're dealing with huge files with inconsistent metadata. The primary
goal is to process the data so validating the post conflation is as
efficient as possible. Conflating large datasets can be very time
consuming, so working with smaller files generates results quicker for
the area you are focused on mapping.

The other goal is to prepare the data for [Tasking
Manager (TM)](https://wiki.openstreetmap.org/wiki/Tasking_Manager). TM
has a project size limit of 5000km sq, and since we'll be using the
Tasking Manager, each national forest or park needs to be split into
project sized areas of interest. Each of these is used when creating
the TM project.

When you select a task in the TM project, it'll download an OSM
extract and satellite imagery for that task. We don't really need
those, as we're dealing with disk files, not remote mapping. While
it's entirely possible to use the project sized data extracts, I also
create a custom task boundaries files for TM, and make small task
sized extracts that are relatively quick to conflate and validate.

# Download the Datasets

All the datasets are of course publicly available. The primary
source of the Motor Vehicle Use Map (MVUM) is available from the 
[FSGeodata
Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation),
which is maintained by the [USDA](https://www.usda.gov/). The
Topographical map vector tiles are [available from
here.](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/),
which is maintained by the National Forest Service. OpenStreetMap data
for a country can be downloaded from
[Geofabrik](http://download.geofabrik.de/north-america.html). National
Park trail data is available from the
[NPS Publish](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.TrailNFS_Publish.zip)
site.

# Initial Setup

As we split up the initial datasets this will generate a lot of files
if you plan to work with multiple national forests or parks. I use a
tree structure. At the top is the directory with all the source
files. You also need a directory with the national forest or park
boundaries which get used for data clipping.

Once I have the source files ready, I start the splitting up process
to make data extracts for each forest or park. If you are only working
on one forest or park, you can do this manually. Since I'm working
with data for multiple states, I wrote a shell script to automate the
process.

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
	--forests (-f): Build only the National Forests
	--datasets (-d): Build only this dataset for all boundaries
	--split (-s): Split the AOI into tasks, also very slow
	--extract (-e): Make a data extract from OSM
	--only (-o): Only process one state
	--dryrun (-n): Don't actually write any datafiles
	--clean (-c): Remove generated task files
	--base (-b): build all base datasets, which is slow
	
The locations of the files is configurable, so it can easily be
extended for other forests or parks. This script is in the utilities
directory of this project.

This also assumes you want to build a tree of output directories.

For example I use this layout:

	SourceData
		-> Tasks
			-> Colorado
				-> Medicine_Bow_Routt_National_Forest_Tasks
					-> Medicine_Bow_Routt_Task_[task number]
				-> Rocky_Mountain_National_Park_Task
					-> Rocky_Mountain_National_Park_Task_[task number]
	        -> Utah
				-> Bryce_Canyon_National_Park_Tasks
			etc...
			
All my source datasets are in __SourceData__.   In the __Tasks__
directory I have all the Multi Polygon files for each forest or park. I
create these files by running *update.sh --split*. These are the large
files that have the AOI split into 5000-km sq polygons.

Since I'm working with multiple states, that's the next level, and
only contains the sub directories for all the forests or parks in that
state. Currently I have all the data for all the public lands in
Colorado, Utah, and Wyoming. Under each sub directory are the
individual task polygons for that area. If small TM task sized data
extracts are desired, all of the small tasks is under the last
directory. Those task files are roughly 10km sq.

## Boundaries

You need boundaries with a good geometry. These can be extracted from
OpenStreetMap, they're usually relations. The official boundaries are
also available from the same site as the datasets as a Multi Polygon.

I use the [TM Splitter](tm-splitter.md) utility included in this project
to split the Multi Polygon into separate files, one for each forest or
park. Each of these files are also a Multi Polygon, often a national
forest has several areas that aren't connected.

## Processing The Data

To support conflation, all the datasets need to be filtered to fix
known issues, and to standardize the data. The OpenStreetMap tagging
schema is used for all data.

Each of the external datasets has it's own conversion process, which
is documented in detail here:

* [MVUM](mvum.md)
* [Trails](trails.md)
* [OSM](osmhighways.md)

While it's possible to manually convert the tags using an editor, it
can be time consuming. There are also many, many weird and
inconsistent abbreviations in all the datasets. I extracted all the
weird abbreviations by scanning the data for the western United
States, and embedding them in the conversion utilities. There are also
many fields in the external datasets that aren't for OSM, so they get
dropped. The result are files with only the tags and features we want
to conflate. These are the files I put in my top level __SourceData__
directory.

# Conflation

Once all the files and infrastructure is ready, then I can conflate
the external datasets with OpenStreetMap. Here is a detailed
description of [conflating highways](highways.md). Conflating with 
[OpenDataKit](odkconflation.md) is also documented. The final result
of conflation is an OSM XML file for JOSM. The size of this file is
determined by task boundaries you've created.

If you want to use TM, then create the project with the 5000km sq task
boundary, and fill in all the information required. Then select your
task from the TM project and get started with validation.

## Validation

Now the real fun starts after all this prep work. The goal is to make
this part of the process, validating the data and improving OSM as
efficient as possible. If it's not efficient, manual conflation is
incredibly time-consuming, tedious, and boring. Which is probably why
nobody has managed to fix more than a small area.

The conflation results have all the tags from the external datasets
that aren't in the OSM feature or have different values. Any existing
junk tags have already been deleted. The existing OSM tags are renamed
where they don't match the external dataset, so part of validation is
choosing the existing value or the external one, and delete the one
you don't want. Often this is a minor difference in spelling.

If the conflation has been good, you don't have to edit any features,
only delete the tags you don't want. This makes validating a feature
quick, often in under a minute per feature. Since many remote MVUM
roads are only tagged in OSM with __highway=track__, validating those
is very easy as it's just additional tags for *surface*, *smoothness*,
and various access tags.

In the layer in JOSM with the conflated data, I can select all the
modified features, and load them into the
[TODO plugin](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/TODO_list). Then
I just go through them all one at a time to validate the conflation. I
also have the original datasets loaded as layers, and also use the
USGS Topographical basemaps in JOSM for those features I do need to
manually edit. Even good conflation is not 100%.
