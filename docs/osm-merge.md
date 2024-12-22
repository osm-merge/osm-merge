# Conflator Program

osm-merge is a program that conflates building footprint data with
OpenStreetMap data to remove duplicates. The result of the conflation
process is buildings that only exist in the footprints data file.

This program can process data from either a postgres database, or data
files in geojson, shapefile format. One of the core concepts is using
a data file of polygons to filter the larger datasets, since a
database may contain multiple countries.

The process of setting up for large scale conflation is in [this
document](conflation.md).

# Command Line Options

## Common Options

These are the nost commonly used options.

    --help(-h)       Get command line options
    --verbose(-v)    Enable verbose output
    --boundary(-b)   Specify a multipolygon for boundaries, one file for each polygon
    --project(-p)    Tasking Manager project ID to get boundaries from database
    --osmdata(-x)    OSM XML/PBF or OSM database to get boundaries (prefix with pg: if database)
    --outdir(-o)     Output file prefix for output files (default "/tmp/tmproject-")
    --footprints(-f) File or building footprints Database URL (prefix with pg: if database)
    --dbhost(-d)     Database host, defaults to "localhost"
    --dbuser(-u)     Database user, defaults to current user
    --dbpass(-w)     Database user, defaults to no password needed

## Tasking Manager Options

These options are used to dynamically extract a project boundary from
a Tasking Manager database. A more common usage is to use the
[splitter.py](tm-splitter.md) program to download the project boundary
from the Tasking Manager itself.

    --splittasks     When using the Tasking Manager database, split into tasks
    --schema         OSM database schema (pgsnapshot, ogr2ogr, osm2pgsql) defaults to "pgsnapshot"
    --tmdata(-t)     Tasking Manager database to get boundaries if no boundary file prefix with pg: for database usage, http for REST API

## OSM Options

When extracting administrative boundaries from an OpenStreetMap
database, the default admin levl is 4, which is commonly used for
couty boundaries. This lets the user select what level of
administrative boundaries they want.

    --admin(-a)      When querying the OSM database, this is the admin_level, (defaults to 4)

## Examples

> PATH/conflator.py -v -x 12057-osm.geojson -f 12057-ms.geojson -o 12057

This takes two disk files, which have already been filtered to only
contain data for the area to conflate.

> PATH/conflator.py -v -x pg:kenya -b 12007-project.geojson -f 12057-ms.geojson -o 12057

This uses a database that contains all of Kenya, but we only want to
process a single project, so that's supplied as the boundary. The
foorptin data was already filtered using
[ogr2ogr](https://gdal.org/programs/ogr2ogr.html), and the project ID
is used as the prefix for the output files.

> PATH/conflator.py -v -x pg:kenya -b 12007-project.geojson -f pg:kenya_footprints -o 12057 -d mapdb -u me

This is the same except the database is on a remote machine called
_mapdb_ and the user needs to be _me_.

> PATH/conflator.py -t tmsnap -p 8345 -b pg:kenya_foot -o pg:Kenya

Reads from 3 data sources. The first one is a snapshot of the Tasking
Manager database, and we want to use project 8345 as the boundary. The
two data sources are prefixed with "pg", which defines them as a
database URL instead of a file. The database needs to be running
locally in this case.
