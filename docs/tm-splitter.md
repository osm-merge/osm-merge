# TM Splitter Utility

This is a simple utility for task splitting to reduce large datasets
into more manageble sizes. It is oriented towards generating a
MultiPolyon or Polygons which can then be be used by ogr2ogr or osmium
for making data extracts.

## Administrative Boundaries

The administrative boundary files are a MultiPolygon of every national
forest, park, or wilderness aea in the United States. Using the
__--split__ option creates a MultiPolygon of each region that can be
used to make data extracts using ogr2ogr or osmium. Each output file
has the name of the region as the filename.

This is only useful if you are just getting started on a large
mapping campaign. For OSM Merge, this splits all the public lands
into a file that can then be furthur split.

## Grid Creation

Once the files for each region have been generated, they are still
large. Next a grid can be generated from each region as a
MultiPolygon. Each task in the grid is the maximum size supported to
create a Tasking Manager project, which is 5000km square.

# Task Creation

To create a file for making data extracts, the grid can be further
split into indivigual files for to use with ogr2ogr or osmium.

# Options

	Usage: tm-splitter [-h] [-v] [-g] [-m] [-s] -i INFILE [-o OUTFILE]

	options:
	-h, --help                     show this help message and exit
	-v, --verbose                  verbose output
	-s, --split                    Split Multipolygon
	-g, --grid                     Create a grid from an AOI
	-m, --meters                   Square area in meters
	-i INFILE, --infile INFILE     The input dataset
	-o OUTFILE, --outfile OUTFILE  Output filename
