# Utility Programs

To conflate external datasets with OSM, the external data needs to be
converted to the OSM tagging schema. Otherwise comparing tags gets
very convoluted. Since every dataset uses a different schema, included
are a few utility programs for converting external datasets. Currently
the only datatsets are for highways. These datasets are available from
the [USDA](https://www.usda.gov/), and have an appropriate license to
use with OpenStreetMap. Indeed, some of this data has already been
imported. The files are available from the 
[FSGeodata Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation)

Most of the fields in the dataset aren't needed for OSM, only the
reference number if it has one, and the name. Most of these highways
are already in OSM, but it's a bit of a mess, and mostly
invalidated. Most of the problems are related to the TIGER import
in 2007. So the goal of these utilities is to add in the [TIGER
fixup](https://wiki.openstreetmap.org/wiki/TIGER_fixup) work by
updating or adding the name and a reference number. These utilities
prepare the dataset for conflation.

There are other fields in the datasets we might want, like surface
type, is it 4wd only, etc... but often the OSM data is more up to
date. And to really get that right, you need to ground truth it.

## [mvum.py](mvum.md)

This converts the [Motor Vehicle Use Map(MVUM)](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip) dataset that contains
data on highways more suitable for offroad vehicles. Some require
specialized offroad vehicles like a UTV or ATV. The data in OSM for
these roads is really poor. Often the reference number is wrong, or
lacks the suffix. We assume the USDA data is correct when it comes to
name and reference number, and this will get handled later by
conflation.

## [trails.py](trails.md)

This converts the [NPSPublish](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.TrailNFS_Publish.zip) Trail dataset. These are hiking trails
not open to motor vehicles. Currently much of this dataset has empty
fields, but the trail name and reference number is useful. This
utility is to support the OpenStreetMap US [Trails Initiative](https://openstreetmap.us/our-work/trails/).

## [usgs.py](usgs.md)

This converts the raw data used to print Topographical maps in the
US. This obviously is a direct source when it comes to names if you
want to be accurate. Although things do change over time, so you still
have to validate it all. The files are available from the
[National
Map](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/). I
use the Shapefiles, as the different categories are in separate files
inside the zip. Each one covers a 7.5 quad square on a topo map. These
have to be merged together into a single file to be practical.

## [osm2favorites.py](osm2favorites.md)

This is a utility to convert a GeoJson file to a GPX files with the
proper icons and colors for [OsmAnd](https://osmand.org). This is
primarily used when out ground-truthing to have entries in the
Favorites menu for the locations we want to validate.

## [odk2osm.py](odk2osm.md)

This program is for converting the output files used by
[OpenDataKit](https://en.wikipedia.org/wiki/ODK_%28software%29)
into an OSM tagging schema. This includes the CSV and JSON files
available from [ODK
Central](Central](https://docs.getodk.org/central-intro/)), to the XML
instances files pulled directly off a mobile device. Using the
instance files enables you to process ODK Collected files when working
offline.

## [blm.py](blm.md)

This converts all the official datasets from the BLM to GeoJson for
but using an OSM tagging schema used for updating OSM.

## [tm-splitter](tm-splitter.md)

This is a utility for processing map data into tasks, offering similar
functionality to the HOT [Tasking Manager](https://tasks.hotosm.org/),
but runs in a terminal for batch processing. This inclides generating
a task grid, and using that to make smaller task sized data extracts.

## [egress.py](egress.md)

This is a program that calculates the shortest emergency egress route
for an area, like an entire county. This generates a GPX file for each
house with several evacuation route possibilities to major highway.

## [osmhighways.py](osmhighways.md)

On the OSM wiki, there is a list of [incorrect
tagging](https://wiki.openstreetmap.org/wiki/United_States_roads_tagging#National_Forest_Road_System)
for forest highway names. Basically the name shouldn't be something
like *"Forest Service Road 123.4A"*. That's actually a reference
number, not a name. This is primarily a problem with existing OSM
data. These would all have to get manually fixed when validating in
JOSM, so this program automates the process so you only have to
validate, and not edit the feature. This also extracts only highway
linestrings, so is used to create the OSM dataset for
conflation. Since the other external datasets also correctly use
name, ref, and ref:usfs, this simplifys conflation. Otherwise the
algorithm would get very complicated and hard to maintain.

## geojson2poly.py

This is a very simple utility to convert a GeoJson boundary
Multipolygon into an [Osmosis *poly* file](https://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format). This can be used with
[osmium](https://wiki.openstreetmap.org/wiki/Osmium), or
[osmconvert](https://wiki.openstreetmap.org/wiki/Osmconvert) to make
data extracts.
