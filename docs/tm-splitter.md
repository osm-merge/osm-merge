# TM Splitter Utility

This is a simple utility for task splitting to reduce large datasets
into more manageble sizes. It uses the concept of tasks of a specified
size. Each project Area Of Interest (AOI) is first turned into a grid
of tasks as a MultiPolygon. Then that MultiPolygon can be used to
generate data extracts of GeoJson files (an external dataset) or OSM
data. The data extracts of OSM data are currently highways only.

The functionality of this script (other than generating the task
grid) can be done by a combination of osmium and ogr2ogr. But each
requires using the correct command line arguments, plus adds more
dependencies. Both of these programs are very useful, but all we
needed is tag filtering and data extracts. This program reduces the
complexity of the dataflow needed for large scale conflation.

## Administrative Boundaries

The administrative boundary files are a MultiPolygon of every national
forest, park, or wilderness aea in the United States. Using the
__--split__ option creates a MultiPolygon of each region that can be
used to make data extracts using ogr2ogr or osmium. Each output file
has the name of the region as the filename.

This is only useful if you are just getting started on a large
mapping campaign. For OSM Merge, this splits all the public lands
into a file that can then be furthur split. Some public lands have
very small building sized polygons in the data, so can be deleted as
we're focused on highways. There may be other bugs as well,
LineStrings instead of Polygons, etc... tm-splitter is tolerant of the
internal geometry variations of the official data sources.

## Grid Creation

Once the boundary MultiPolgon files for each region have been
generated, they are still large. Next a grid can be generated from
each region as a MultiPolygon. Each task in the grid is the maximum
size supported to create a HOT Tasking Manager project, which is
5000km square.

## Data Extracts

TM-Splitter can use the generate MultiPolygon to make data extracts of
Geojson or OSM files. These extracts are clipped to each task
boundary. Any highway that intersets the boundary is complete with the
nodes in other tasks added.

# Options

Usage: tm-splitter [-h] [-v] -i INFILE [-g] [-s] [-o OUTFILE] [-m METERS] [-e EXTRACT]

This program manages tasks splitting

	options:
	-h, --help             show this help message and exit
	-v, --verbose          verbose output
	-i, --infile INFILE    The input dataset
	-g, --grid             Generate the task grid
	-s, --split            Split Multipolygon
	-o, --outfile OUTFILE  Output filename template
	-m, --meters METERS    Grid size in kilometers
	-e, --extract EXTRACT  Extract data for Tasks

# Examples

To break up a large public land boundary, a threshold of 0.7 gives
us a grid of just under 5000 sq km, which is the TM limit.

	tm-splitter.py --grid --infile boundary.geojson 

To split the grid file file into tasks, this will generate a separate
file for each polygon within the grid. This file can then also be used
for clipping with other tools like ogr2ogr, osmium, or osmconvert.

	tm-splitter.py --split --infile tasks.geojson

