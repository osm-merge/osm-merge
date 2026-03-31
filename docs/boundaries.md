# Boundaries

Good boundaries are critical to being able to chop the large files
into manageable pieces.

# Boundary Sources

## OpenStreetMap

It is possible to pull boundaries out of OpenStreetMap, but a warning,
many aren't very good. In OSM, some boundaries are a Way (Polygon)
some are relations, some are missing sections. Extracting many
boundaries is not for the faint of heart... There is a
[website](https://osm-boundaries.com/) attempting to do this. If you
only need a few boundaries, OSM works fine, but you might have to do a
little manual cleanup.

## Administrative Sources

I use official administrative boundary datasets. While these are all
public domain, I have no interest in uploading them to OSM, which
would be a whole other project. And I only need them for data chopping
anyway. You can get the official boundaries from these two sources.

[National Forests](https://data.fs.usda.gov/geodata/edw/edw_resources/fc/S_USA.AdministrativeForest.gdb.zip)

[National Parks](https://catalog.data.gov/dataset/administrative-boundaries-of-national-park-system-units-national-geospatial-data-asset-ngd-a4761)

These datasets are national wise, so need to be split into each forest
or park. I wrote a program called 
[tm-splitter](https://github.com/osm-merge/osm-merge/blob/main/osm_merge/utilities/tm-splitter.py)
that reads in the large file, and then splits each forest and park into
a standalone file. This standalone file is a Multi-polygon, as many
forests have multiple sections that aren't actually connected. But at
this point, you have small enough boundaries to start on making data
extracts for conflation.

# Boundary Problems

Most of the National Park boundaries are often a single polygon, as
many national parks are smaller than national forests. National Forest
boundaries have an interesting set of problems that need to be cleaned
up before they're usable.

## Small Out-holdings

National Forests often have multiple small Polygons that are outside
of the actual forest boundary. These appear to be administrative
buildings. Ranger stations, visitors centers, etc... These are all
useless for our goal of improving remote trails and highways.

When the tm-splitter utility parses each Multi-polygon into it's
individual Polygons, these small out-holdings are ignored, leaving only
the actual forest boundaries.

## Inner Polygons

Since we're only interested in using these boundaries for making data
extracts, some have interior Polygons that have other ownership or
public land designations. Since we're using boundaries to make data
extracts, I may drop all inner Polygons, but so far they don't see to
cause any problems.
