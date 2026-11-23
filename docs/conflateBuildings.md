# conflateBuildings.py

This is a program for conflating building footprints between
OpenStreetMap and AI generated building footprints from Microsoft or
Google.

## Preparing The Data

When conflating using GeoJson files, there are issues with the data
extract size which cause performance issues. Conflation is a brute
force algorythm. OpenStreetMap data for an entire state is available
from
[GeoFabrik](https://download.geofabrik.de/north-america/us.html). Building
footprints are available from the Overture Foundation, Microsoft, and
Google. I've been working with county sized datasets, which seems to
be a good size. You need to have the county boundaries as Polygons to
split up the state sized files. You can split up the datasets using
either [ogr2ogr](https://gdal.org/programs/ogr2ogr.html), or my
[tm-splitter](tm-splitter.md) program.

## First Step

The first step is to conflate OpenStreetMap data with the building
footprints. I use an extract that is only buildings. You can filter
the source using ogr2ogr, or
[osmium](https://osmcode.org/osmium-tool/). I prefix an identifer so I
can tell which dataset they are, but you can use any name. This
example is for Jefferson County, Colorado. The conflation program can
also use a MultiPolygon file to clip the datasets, but I usually just
use a short bash script.

```
conflateBuildings.py  -v -o Colorado/Buildings/osm-JeffersonCounty.geojson  -f Colorado/Buildings/blds-JeffersonCounty.geojson
```

This will create a */tmp/new-buildings.geojson* file containing only
building footprints not in OpenStreetMap. The building footprints data
is of uneven quality, so you have to manually validate each feature. 

## Next Step

OpenStreetMap prefers to have the address on the building polygon, so
if you have statewise address data, you can then conflate that with
the buildings. This produces an output file of all the buildings, and
if they have an address, that is added to the building tags.

```
conflateBuildings.py  -v -a Colorado/Buildings/addr-JeffersonCounty.geojson  -f /tmp/new-buildings.geojson
```

### Usage

```
usage: conflateDB [-h] [-v] [-f FOOTPRINTS] [-o OSMDATA] [-a ADDRESSES] [-b BOUNDARY]

This program conflates external data with existing features from OSM.

options:
  -h, --help            show this help message and exit
  -v, --verbose         verbose output
  -f, --footprints FOOTPRINTS
                        Building footpints data Source
  -o, --osmdata OSMDATA
                        OpenStreetMap data Source
  -a, --addresses ADDRESSES
                        Address data Source
  -b, --boundary BOUNDARY
                        Boundary polygon to limit the data size
```
