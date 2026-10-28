# Emergency Egress Planning

This program is a little different from all the other programs in this
project in that it is a data consumer, instead of data creator. I'll
not that this project project requires good map data with consistent
tagging. While the results of this are not 100%, the quality of the
results depends on the quality of the data. I have only used this in
my local county, as here I know the map quality was good as I've
mapped here for over a decade.

This program also requires using two PostgreSQL databases. One holds the
current OSM data, and the other one for
[PGRouting](https://pgrouting.org/), which is the same OSM highway
data, but uses a different schema to support routing functionality.

This is obviously an experimental program, but is an aid to decision
making for mass evacuation events. As those events are usually
chaotic, this is more for pre-event planning for emergency
responders. This is also focused on rural areas with poor access,
although I assume it could support urban areas.

## What Does This Do

The basic problem is in my rural county surrounded by national forest
land is also very steep mountain terrain. Housing here is a mix of
sparse cabins on old mining claims up dirt roads, or small
developments, usually an old ranch that got sold to developers. Most
of these have only one or two ways in and out to a major
road. Most of these are small, but 16 subdivisions are over 50
households, which is enough for a traffic jam.

The idea was to split up the households in these more densely populated
areas to the closest egress route to a major highway. It also takes
into account other criteria for emergency egress where a jeep track
might also be an appropriate emergency route for people with
high-clearance vehicles, which are common around here. And last is
walking out, as sometimes the egress roads are usable anymore due to
wildland fire or flooding. This is more critical for the subdivisions
which only have one access road.

## What This Doesn't Do

Right now this does not support adding barriers, which is on the TODO
list. This would let me add a way to close a road someplace and then
recalculate all the evacuation route to avoid the obstacle. This
would probably require a better UI than what is currently supported
which is terminal based. A web front end would be a nice contribution.

# Importing The Data

First create the OSM database. I usually start by downloading the
state I plan to analyze from
[GeoFabrik](https://download.geofabrik.de/north-america/us.html). Start
by creating the database and installing the two extensions we'll need.

```c
	createdb colorado
	psql -c "CREATE EXTENSION postgis"
	psql -c "CREATE EXTENSION pgrouting"
```

Once the database is created, then the OSM file needs to be
imported. I use the __importer__ utility program in the 
[osm-rawdata](https://hotosm.github.io/osm-rawdata/) project, which I
am also the author of. This uses a database schema designed to support
data analysis tasks like conflation.

For the PGRouting database, he easiest way to import is to use the
[osm2pgrouting](https://github.com/pgrouting/osm2pgrouting), which
does the full setup. It is possible to add fields to the tables in an
OSM database and use it for routing, but I think using two databases
will be easier to keep updated.

## OSM Database

This database is used for two tasks, one is to get the list of house
addresses, and the other to get the highway data. This is not used for
routing. As these are commonly an entire state, that would be too much
data for process. While it is possible to make a smaller data extract
and use that for the database, this program also support passing a
MultiPolygon boundary file, for example my local county.

The schema is different from the default one used by most OSM
programs. The big difference is the default database schema keeps node
in a separate table from the ways used for highways. Any spatial
access requires to de-reference the nodes used by the way for it's
coordinates. The other problem with the default schema is some tags
are columns, some are in an hstore or jsonb column, so SQL queries are
messy. The modified schema include all the coordinates with the
highway way, and also puts all tags under a single column. This both
simplifies SQL queries, and is much faster when doing spatial
analysis.

## PGRouting Database

The PGRouting database has two primary tables, __ways_vertices_pgr__
and __ways__. The ways_vertices_pgr table are the nodes for the
intersection of two highways. Each vertex has an ID which is not the
same as the OSM ID. The main columns used are __id__ and __geom__. The
geometry of each node comes from the OSM data where the two highways
connect.

The __ways__ table has OSM highway data, but lacks the OSM
tags. Instead it adds many new columns to support routing like the
cost of a particular highway segment, the speed limit, the highway
geometry.

## The Algorithm

This is still a bit experimental, so may change, but the basic
implementation is working.

### Getting the OSM Data

Initially the program queries the OSM database, filtered by an
optional boundary MultiPolygon and gets a list of all the household
addresses in the area you want to analyze. Then the OSM database is
queried to get all the major highways. These are the ones that would
support higher volume traffic, so the desired target for an
evacuee. The criteria is simple, the highway needs to be tagged with
either primary, secondary, or tertiary. Some other criteria like
*surface* tag aren't used as around here not all major highways are
paved.

Once the list of major highways is made, it's geometry is enhanced by
making a buffer around the LineString. Comparing floating point
numbers can be messy, so this supports using *ST_CONTAINS* in SQL
queries instead.

### Getting The Routing Data

Once the OSM data has been loaded into the program it then queries the
__ways_vertices_pgr__ table for all the routing IDs for the OSM highway
geometry. As the vertices are also OSM nodes, the geometries are the
same. The routing ID is later used to determine when the major highway
is reached. A buffer is created around each vertex to find others
within a specified distance. This is looking for the nearest vertex,
preferably the driveway for the house. That vertex is used as the
*source* data for the routing.

Then we need to find the target vertices on one if the major
highways. A wider buffer is created, and only vertices on the major
highway are queried. Once we have the source (the house) and the
targets, we can then use PGRouting to generate routes.

### Routing Data

The PGRouting function *pgr_dijkstra* will generate a list of possible
routes. For example the ID of the vertex by the home is 4135, and
three targets were found to navigate to.

	SELECT res.path_seq, res.node, res.edge, ST_AsText(e.geom), res.cost, e.reverse_cost, e.reverse_cost_s FROM pgr_dijkstra('SELECT id as id, source, target, cost_s AS cost FROM ways', 4135, ARRAY[1387, 1388, 6005, 183], directed := false) AS res JOIN ways e ON res.edge = e.id;

This will generate a list of routes, each route itself is a list of
highway segments. ST_AsText(geom) is used to generate WKT format,
which is the easiest way to pass geometries between python and
SQL. Each segment of a potential route is processed into a
LineString. The target ID of each segment is compared to the the list
of routing IDs for each of the major highways, and if it's in the
highway buffer zone to determine to stop processing the route.

Each route is then used to generate a GPX file of GPX tracks, one for
each route. Each GPX file is for a single house address. You can use
the *gpxmerge* program to combine them into a single file if you
want. I use *gpxsee* validating output files as it's fast, and also
QGIS when I need to analyze the data deeper. Also QGIS lets me display
the PGRouting database with the GPX tracks, which is useful for
debugging.

## Usage

```c
Calculate route to the nearest decent highway

options:
  -h, --help            show this help message and exit
  -v, --verbose [VERBOSE]
                        verbose output
  -b, --boundary BOUNDARY
                        Optional boundary to clip the data
  -o, --outfile OUTFILE
                        The output file
  -u, --osmuri OSMURI   OSM Database URI
  -r, --routedb ROUTEDB
                        PGRouting Database URI

This program uses OpenStreetMap data to calculate egress routes to ther nearest
decent hoghway for mass evacuation during an emergency. Decent being primary,
secondary, or tertiary. This produces a GPX file with the route suggestions, one
for each address in the AOI.

  For example:

	egress.py -v -u localhost/colorado -r localhost/gilpin_routing -b boundaries/Gilpin.geojson

    --boundary
        Must be a MultiPolygon or Polygon.
    --osmuri
        OSM data imported with osm-rawdata's importer program
    --routedb
        Imported with the osm2pgrouting program in PGRouting
```

