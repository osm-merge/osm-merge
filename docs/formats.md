# File Formats

This project support two file formats, [GeoJson](https://geojson.org/)
and [OSM XML](https://wiki.openstreetmap.org/wiki/OSM_XML). 

## GeoJson

GeoJson is widely supported by many tools, and this project uses it as
the internal data structure for consistency. At the top level the file
starts with a *GeometryCollection*, which is just a container for the
list of features.

### Geometry

Each GeoJson feature contains a geometry object that has two fields,
the *coordinates*, and the *type*. Shapely or GDAL can be used to
convert between string representations and geometry objects.

### Properties

The properties is the array of __keyword=value__ pairs, similar to the
tags in OSM. There is no definition of a schema, and pair works. For
conflation though, standardizing on the OSM schema for tagging pairs is
critical to keep things simple.

	"properties": {
		"ref:usfs": "FR 965.2",
		"name": "  Road",
		"4wd_only": "yes",
		"seasonal": "yes"
	},

## OSM XML

An OSM XML file is read and converted to GeoJson, and then later it
can get converted to OSM XML for the output file. In addition to the
tags and geometry, each feature also has attributes.

### Attributes

The OSM XML format has attributes, which are used to control editing a
feature. Since this project wants to generate an OSM XML file for
JOSM that allows for tag merging, these attributes are important. In
the post conflation data file, the version of the existing OSM feature
has been incremented, and the __action__ is set to *modify*. This enable
JOSM to see this as an edited feature so it can be uploaded.

- id - the OSM ID of the feature
- version - the current version of the feature
- action - the action to apply when uploading to OSM
	- create
	- modify
	- delete
- timestamp - the timestamp of the feature's last change

With __action=modify__ set, in JOSM you can *update modified* and sync
with current OSM.

### Data Types

There are two data types in the OSM XML files used for
conflation. These are nodes and ways.

### Nodes

A node is a single coordinate. This is often used as a POI, and will
have tags. A node that is referenced in a way won't have any tags,
just the coordinates. The version and timestamp get updated if there
is a change to the node location.

	<node id="83276871" version="3"
	    timestamp="2021-06-12T16:25:43Z" lat="37.6064731" lon="-114.00674"/>

### Ways

A way can be a linestring, polygon, any geometry that includes more
than one node. This makes it difficult to do spatial comparisons, so
when an OSM XML file is loaded, in addition to the refs, they are also
converted to an actual geometry. All the calculations use the
geometry, and the refs are used to construct the OSM XML output file
for JOSM. OSM has no concept of a LineString or Polygon, the shape is
determined by the tags, for example __highway=track__, or
__building=yes__.

	<way id="10109556" version="4" timestamp="2021-06-12T15:42:25Z">
    <nd ref="83305252"/>
    <nd ref="8118009676"/>
    <nd ref="8118009677"/>
    <nd ref="83277113"/>
    <nd ref="83277114"/>
    <nd ref="83277116"/>
    <nd ref="83277117"/>
    <tag k="highway" v="unclassified"/>
    <tag k="surface" v="dirt"/>
  </way>

## Converting Between Formats

To support reading and writing OSM XML files, this project has it's
own code for parsing OSM XML and GepoJson data files. When parsing OSM
XML files, the data is stored internally as GeoJson. When writing an
OSM XML output file, this data structure is converted to OSM XML.
All of the attributes in the OSM XML file being read are convert to
tags in the GeoJson properties section, and then later converted from
the properties back to OSM XML attributes when writing the output
file.
