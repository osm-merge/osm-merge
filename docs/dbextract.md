# DB Extract

This is a simple utility to make data extracts from a postgres
database containing OpenStreetMap data. Currently it only supports
highways, and is focused on creating a data extract that can be used
for conflation. While this works fine on a static database, more
importantly it can use a database of OSM data updated every minute.

This database can be kept up to date using the
[Underpass](https://github.com/emi420/underpass) programs. This
program uses the actual changeset files to update the data, same as
Overpass would do. It uses a *priority.geojson* file to limit the
geographical area too keep updated as most people don't need the
entire planet.

## Output Files

Dbextract can output a GeoJson or a OSM XML output file. Currently the
OSM XML output file only contains __ways__, so no data is visible. To
get the nodes, in JOSM execute *File->update data* and they'll be
visible. This restriction will be gone after the bug in Underpass is
fixed.

## Examples

To generate an OSM XML data file for a small AOI, do this:

	dbextract.py -v -b Dixie_Task_1.geojson -u localhost/uri -o out.osm

To generate an GeoJson data file from the entire database, do this:

	dbextract.py -v -u localhost/uri -o out.geojson

	Options:
	-h, --help              Show this help message and exit
	-v, --verbose [VERBOSE] Verbose output
	-b, --boundary BOUNDARY Optional boundary to clip the data
	-o, --outfile OUTFILE   The output file (*.osm or *.geojson)
	-u, --uri URI           Database URI
