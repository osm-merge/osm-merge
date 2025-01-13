# OSM Merge, a Community Project of OpenStreetMap US

📖 **Documentation**: <a href="https://osm-merge.github.io/osm-merge/" target="_blank">https://osm-merge.github.io/osm-merge/</a>

🖥️ **Source Code**: <a href="https://github.com/osm-merge/osm-merge" target="_blank">https://github.com/osm-merge/osm-merge</a>

---

## Background

This is a project for conflating external map datasets with
OpenStreetMap with the ultimate goal of importing it into
[OpenStreetMap](https://www.openstreetmap.org). It
is oriented towards processing non OSM external datasets and supports
conflation of field data collection using
[OpenDataKit](https://opendatakit.org/software/), as well as other
external datasets.

The goal of this project is focused on improving remote highway and
trail metadata to assist with emergency and recreational access in
remote areas. This project uses several data sources to improve the
existing highway features in OpenStreetMap. The current data in
OpenStreetMap was often imported complete with bugs in the 
original dataset, or the only details are *highway=track*. All of
these have a US forest service reference number and name. Adding those
makes it much easier to identify where you are and to communicate a
location over a radio or phone.

There is also access information in the datasets that is useful. This
includes access for vehicle types, horses, public/private, etc... that
is useful for OpenStreetMap.

![Way up Rollins Pass](https://github.com/osm-merge/osm-merge/blob/main/docs/assets/small-rollinspass.png)

The other goal of this project is to support field data collection
using OpenDataKit. The
[fieldwork
scripts](https://github.com/osm-merge/osm-merge/tree/main/osm_merge/utilities)can
be used to convert the ODK data files into
[GeoJson](https://geojson.org/) and [OSM
XML](https://wiki.openstreetmap.org/wiki/OSM_XML). This
project then supports conflating that field collected data with
current OpenStreetMap. Otherwise this is a time-consuming process to
do manually. This can be used with the [Field Mapping Tasking Manager (FMTM)](https://fmtm.hotosm.org) to process the collected data for validation
and uploading to OpenStreetMap.

![Women field mapping](https://github.com/osm-merge/osm-merge/blob/main/docs/assets/small-zanzibar.jpg)

## External Datasets

I'm working on a website for all the converted and processed data
files that covers every national park or forest for the entire US.
From the US forest service there are several datasets with a good
license for OpenStreetMap. Warning, these are large files, so hard to
work with at first. This project uses a huge amount of data (and disk
space) if you start from the original nation wide datasets, which are
too large to edit. There is a contrib script in the git sources I use
to start breaking down the huge files into managable pieces.

The MVUM data hasn't changed in years, so splitting everything up is a
one-time task. For OpenStreetMap extracts all the data extracts of
highways can be regenerated in a few hours, so it's possible to stay
closely in sync with upstream. The original files are available from
these sources.

### US Forest Service data

* Motor Vehicle Use Maps [(MVUM)](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip)
* [USFS Trail maps](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.TrailNFS_Publish.zip)

### US Park Service data

* [NPS Trails](https://public-nps.opendata.arcgis.com/search?collection=Dataset&q=trail)

### For OpenStreetMap

* [Geofabrik](http://download.geofabrik.de/north-america.html)

Much of the process of conflation is splitting huge datasets into
managable sized files for data processing. I have that process [mostly
automated](https://github.com/osm-merge/osm-merge/blob/main/contrib/update.sh) so I
can easily regenerate data extracts any time I make improvements to the
conversion process. Currently there isn't any conflated data yet, just the
convered data files chopped into manageable sized files. The processed
map data is available [from
here](https://osmmerge.org/). Feedback on the data conversion to
OpenStreetMap tagging is appreciated.

![Skipped highway segments](https://github.com/osm-merge/osm-merge/blob/main/docs/assets/skippedsegments.png)

## Programs

This project comprises of a main program, and multiple utilities. The
utilities are used to prepare the datasets for conflating by fixing
known bugs. It is very difficult to conflate datasets with wildly
different data schemas, so making all the data use a consistent schema
is important so tags can be compared.

### Utilities

The utility programs are used for all data cleaning and other tasks
needed to conflate the data files. Known bugs in the datasets are
fixed where possible, for example, expanding abbreviations so *Rd*
becomes *Road*, etc... and also drops all the extraneous fields that
aren't for OpenStreetMap. The fields we are most interested in are the
name, the official reference number, and the access values.

* tm-splitter.py
    * Generate task grids for the Tasking Manager
* mvum.py
    * Convert forest service MVUM datasets to OpenStreetMap
* trails.py
    * Convert forest service datasets to OpenStreetMap
* usgs.py
    * Convert USGS topographical datasets to OpenStreetMap
* osmhighways.py
    * Data janitor for OpenStreetMap, delete *tiger:*, etc...

### Conflator Program

This program doesn't require a database, unlike the other conflation
programs in this project, although adding database support is on the
TODO list. It is focused on conflating [rural highways](highways.md)
and [hiking trails](trails.md). It can also [conflate
OpenDataKit](odkconflation.md) with OpenStreetMap.

It supports conflating any two datasets in either GeoJson or OSM
format. While this is currently under heavy development and
debugging. I've been processing large amounts of data to track down
all the obscure bugs in the original datasets, or the conflation
process.

![MVUM Signs](https://github.com/osm-merge/osm-merge/blob/main/docs/assets/20210913_113539.jpg)

## Contributing

Anyone motivated is welcome to contribute to both the software, or
just using these tools and the data for your own map
improvements. This is a huge amount of data, as the original
source files are nationwide. I'm just focused on my part of the
western US. Help improving OpenStreetMap accuracy in remote areas
of your own state is a good idea, and can save lives in an
emergency. Be a data janitor!
