# Mapper Data flow

Much of the process of conflation is preparing the datasets since
we're dealing with huge files with inconsistent metadata. The primary
goal is to process the data so validating the post conflation is as
efficient as possible. Conflating large datasets can be very time
consuming, so working with smaller files generates results quicker for
the area you are focused on mapping.

It is also possible to use the pre or post conflation data files in
JOSM without the Tasking Manager if the density of the data per task
isn't too large. 100 Highways or less seems to be the most efficient
density per task. Included in this project is a utility,
[TM Splitter](https://osm-merge.github.io/osm-merge/tm-splitter/) that
can be used to generated a grid of tasks that are smaller if you have
the project boundary (AOI).

## Tasking Manager

The other goal is to prepare the data for [Tasking
Manager (TM)](https://wiki.openstreetmap.org/wiki/Tasking_Manager). TM
has a project size limit of 5000km sq, which is also a good size when
not using the TM. Each national forest or park needs to be split into
a grid of TM sized tasks. Each of these is used when creating the
TM project.

When you select a task in the TM project, it'll download an OSM
extract and satellite imagery for that task. We don't really need
those, as we're dealing with disk files, not remote mapping. While
it's entirely possible to use the TM project sized data extracts, I
also create a custom task boundaries files for TM, and make small task
sized extracts that are relatively quick to conflate and validate.

# Getting The Data

To make any progress. obviously data is needed. Often getting the data
and processing it can be the hard part for a mapper wanting to improve
the metadata in OSM for remote highways and trails in one area. While
the nationwide data sets are available. it can be tedious and time
consuming to manage all the data.

## Data Extracts

This project hosts data extracts broken down by national forest, park,
or wilderness areas on the [OSM Merge](https://osmmerge.org/]) project
website. These are the output files of the conversion and data
cleaning process for MVUM, RoadCore. or Trails data. The conversion
utilities are [documented
here](https://osm-merge.github.io/osm-merge/utilities/). This process
does several things. For external datasets, it drops unnecessary data
fields from the original data schemas, and converts the data fields
suitable for OpenStreetMap into an OSM schema for conflation. For OSM
data extracts, it also correct multiple data quality issues, like
expanding abbreviations, more USFS reference numbers from the *name*
field into the appropriate *ref:usfs** for OSM.

There are other projects for converting the original datasets to OSM
syntax, that do a similar function. Those are
[usfs-to-osm](https://github.com/jake-low/usfs-to-osm) and
[nps-to-osm](https://github.com/jake-low/nps-to-osm), and generate
files that can also be used for conflation.

## Original Sources

All the datasets are of course publicly available. The primary
source of the Motor Vehicle Use Map (MVUM) and RoadCore data is
available from the [FSGeodata
Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation),
which is maintained by the [USDA](https://www.usda.gov/). The
Topographical map vector tiles are [available from
here.](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/),
which is maintained by the National Forest Service. OpenStreetMap data
for a country can be downloaded from
[Geofabrik](http://download.geofabrik.de/north-america.html). National
Park trail data is available from the
[NFS Publish](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.TrailNFS_Publish.zip)
site.

# Initial Setup

## Small Scale

Many mappers are focused on a few (potentially large) areas that
interest them. They are often out ground-truthing the map data (or
lack thereof) in OSM. For the mappers that may want to add metadata
for their favorite areas, this project makes the smaller datasets
available so they can focus on mapping, instead of data manipulation.

These data extracts are available from the project website, and as
legacy datasets, the MVUM, RoadCore, and Trails dataset extracts only
get updated when there are improvements made to the conversion
utilities.

* [National Forests](https://osmmerge.org/SourceData/Forests)
* [National Parks](https://osmmerge.org/SourceData/Parks)
* [National Wilderness](https://osmmerge.org/SourceData/Wilderness)

There are also extracts from OpenStreetMap for each area, as
well. Note that these can be out of date since OSM is constantly
changing. These extracts have been converted as well, so the
guidelines on [automated
edits](https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct)
apply. Each feature must be validated manually, the goal is to make
this validation process as efficient as possible.

The conversion does two primary tasks. One is it drops all the ancient
__tiger:__ tags that the community has decided are meaningless to
OSM. Also non OSM tags from old partial imports like __SOURCEID__ are
also deleted. It also looks for a possible forest service reference
number in the *name* or *ref* field, and moves it to the proper
*ref:usfs*, with a *"FR"* prefix. This saves much cut & paste later
when validating the results.

For more detail on validating the converted and/or conflated files,
there is a detailed document on [validating with
JOSM](validating.md). Since reviewing and updating all the remote
trails and highways for the entire US is a huge task, this project is
very focused on supporting that dataflow for other mappers so they can
concentrate on validating and mapping their favorite areas.

## Large Scale

Maintaining data extracts for multiple areas requires more manual work
than just mapping. For one thing, it'll consume a lot of disk space
and cpu cycles. Setting up a [large scale](setup.md) data extract is
covered in detail in that document.

## Processing The Data

To support conflation, all the datasets need to be filtered to fix
known issues, and to standardize the data. The OpenStreetMap tagging
schema is used for all data. You can skip this section if using data
extracts from the [OSM Merge](https://osmmerge.org) as the conversion
is already done. Or if you are interested in the details of the
conversion process between data formats.

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

Once all the files and infrastructure is ready, then conflating
the external datasets with OpenStreetMap can start. Here is a detailed
description of [conflating highways](highways.md). Conflating with 
[OpenDataKit](odkconflation.md) is also documented. The final result
of conflation is an OSM XML file for JOSM, and a GeoJson for other
editors. The size of this file is determined by task boundaries you've
created.

If you want to use TM, then create the project with the 5000km sq task
boundary, and fill in all the information required. Then select your
task from the TM project and get started with validation.

Conflation uses primary and secondary datasets. Any data in the
primary is considered to be the *official name* or reference
number. Where there is an existing name in OSM, it's changed to an
*alt_name* so it can be manually validated. No data is lost, just
renamed, leaving it up to the mapper to decide.

## Validation

The real fun starts after all this prep work. The goal is to make
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
