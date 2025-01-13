# OpenStreetMap Data

Being crowd sourced and open to all who want to contribute,
OpenStreetMap (OSM) has infinite flexibility in the various tag/values
used for metadata. Many of the tags not in common use are ignored by
the renderers and routing engines, but still live in the database and
data files. You'd really only notice if you're deep in the data, which
is the key to good conflation.

The features in OSM come from a wide variety of sources. Mobile apps,
imports, satellite imagery. Often features traced from imagery are
lacking any tags beyond __building=yes__ or __highway=track__, which
we hope to improve on by conflating with other datasets.

## Data Janitor

Being a data janitor is important, if rather boring and tedious
task. Bugs in the data can lead to navigation problems at the very
least. An accurate and detailed map is a thing of beauty, and often
OSM gets really close.

Unfortunately to conflate OSM data with external data sources, it
needs to be cleaned up. Normally it gets cleaned up by the mapper, who
has to manually review and edit the tags. Since the highway name is an
important item used to confirm a near match in geometry, too much
variety can make this a slow process.

This project has an
[osmhighways.py](https://github.com/osm-merge/osm-merge/blob/main/osm_merge/utilities/osmhighways.py)
program that is used to cleanup some of the problems, like deleting
unnecessary tags, and fixing the name vs reference number
problem. Deleting all bogus tags reduces the data size, which is a
benefit. This project also extracts only highway linestrings, so a
clean dataset for conflating geometries.

## Old Imports

OpenStreetMap (OSM) has a past history of imports, often done way back
when OSM had little highway data. This was a way to bootstrap
navigation, and it mostly worked. 

### TIGER

Since it was publically available, the data [used by the US Census
Department](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-geodatabase-file.html)
was imported around 2007. The data is of varying quality, but was
better than nothing. The OSM community has been cleaning up the mess
ever since. More information on the TIGER fixup can be [found 
here](https://wiki.openstreetmap.org/wiki/TIGER_fixup).

An small example of the tags added from TIGER, all of which can be
deleted.

		<tag k="tiger:name_base" v="75th"/>
		<tag k="tiger:name_base_1" v="75th"/>
		<tag k="tiger:name_direction_prefix" v="N"/>
		<tag k="tiger:name_type" v="St"/>
		<tag k="tiger:name_type_1" v="St"/>
		<tag k="tiger:cfcc" v="A41"/>
		<tag k="tiger:reviewed" v="no"/>

I don't think I've ever seen a __tiger:reviewed=yes__ tag.

### Motor Vehicle Use Map (MVUM)

The MVUM data is highways in national forests, so useful in remote
area not always in TIGER. Or in TIGER but completely wrong. I've seen
roads in TIGER that don't actually exist. All the MVUM data is better
quality as much of the data was mapped by ground-truthing. It has
useful data fields, like is a high clearance vehicle needed, what is
the surface, and other access data like are ATVs allowed ?

[MVUM)](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip

### Clipping

To support conflation, even OSM data needs to be chopped into smaller
pieces. While osmium and osmfilter could so this, I've had problmes
with the other tools when the task polygon is small. The
osmhighways.py program also clips files. Since it's in an OSM data
format, we can't really use shapely, or geopandas, just osmium. It's a
bit slow, being pure python. If it's a continuing problem I'll
refactor it into C++.

There is a question as to whether it's better to clip a highway at the
bundary, or include ther part of it's geometry tha's outside the
boundary. I'm experimenting with both, and seeing how it effects
conflation.

# Options

	-h, --help                     show this help message and exit
	-v, --verbose                  verbose output
	-i INFILE, --infile INFILE     Input data file
	-o OUTFILE, --outfile OUTFILE  Output filename
	-c CLIP, --clip CLIP           Clip data extract by polygon
	-s SMALL, --small SMALL        Small dataset

This program extracts all the highways from an OSM file, and correct as
many of the bugs with names that are actually a reference number.

    For Example:
        osmhighways.py -v -i colorado-latest.osm.pbf -o co-highways.osm

