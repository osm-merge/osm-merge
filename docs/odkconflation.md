# Conflating OpenDataKit with OpenStreetMap

Typically conflation is done when doing data imports, but not
always. Data collected in the field can be considered an
import. Conflating buildings or POIs from external data is relatively
easy as it's already been cleaned up and validated. When you are doing
field mapping, then you have to cleanup and validate the data during
conflation. This is a time consuming process even with good conflation
software.

I've worked with multiple conflation software over the
years. [Hootenanny](https://github.com/ngageoint/hootenanny),
[OpenJump](http://www.openjump.org/) (later forked into RoadMatcher),
etc...  which currently are now dead projects. Conflation is a hard
technical challenge and often the results are poor and
unstatisfing result. For smalller datasets often it's easier to do do
manual conflation using [JOSM](https://josm.openstreetmap.de/) or
[Qgis](https://qgis.org/en/site/). This project tries to simply the
problem by focusing on OpenStreetMap data.

## Smartphone Data Collection

While commercial organizations may use expensive GPS devices, most of
us that do data collection as a volunteer or for an NGO use their
smartphone. Their is a variety of smartphone apps for data collection
that fall ihnto two categories. The first category are the apps like
[Vespucci](http://vespucci.io/),
[StreetComplete](https://streetcomplete.app/), and [Organic
Maps](https://organicmaps.app/). These directly upload to
[OpenStreetMap](https://www.openstreetmap.org). These are great for
the casual mapper who only adds data occasionally and is limited to a
POI. For example, a casual mapper may want to add the restaurant they
are currrently eating in when they notices it's not in
OpenStreetMap. In addition, they probably have a cell phone
connection, so the data gets added right away.

The other category are apps like [ODK Collect](https://getodk.org/),
[QField](https://qfield.org/) [ArcGIS Field
Maps](https://www.arcgis.com/apps/fieldmaps/) which are oriented to
larger scale mapping projects, often offline without any cellular
connection. These collect a lot of data that then needs to get
processed later. And conflation is part of this process.

All of these smartphone based data collection apps suffer from poor
GPS location accuracy. Modern smartphones (2024) are often 5-9 meters
off the actual location, sometimes worse. In addition when field data
collecting, you can't always record the actual location you want, you
can only record where you are standing.

You can improve the location data somewhat if you have a good quality
basemap, for example you see a building within a courthouse wall when
you are standing in the street. If you have a basemap, typically
satellite imagery, you can touch the location on the basemap, and use
that instead of where you are standing. Then later when conflating,
you have a much higher chance the process will be less painful.

## OpenDataKit

[OpenDataKit](https://opendatakit.org/software/) is a
format for data import forms used to collect custom data. The source
file is a spreadsheet, called an
[XLSForm](https://xlsform.org/en/). This gets used by the mobile app
for the quesion and answer process defined by the XLSForm. There are
multiple apps and projects using XLSForms, so it's well supported and
maintained.

The XLS source file syntax is a bit wierd at first, being a
spreadsheet, so the osm-fieldwork project contains tested XLSForm
templates for a variety of mapping project goals. These can be used to
create efficient XForms that are easy to convert to OSM. The primary
task when manually converting ODK collected data into OSM format is
converting the tags. If the XLSForm is created with a focus towards
OSM the XLSForm can make this a much simpler process. This [is
detailed](https://osmmerge.org/tech/ImproveXLSForms.html)
more in this document. Simply stated, what is in the *name* colum in
the XLSForm becomes the *name* of the tag in OSM, and the response
from the choices sheet becomes the value.

### ODK Collect & Central

[ODK Collect](https://getodk.org/) is a mobile app for data collection
using XLSForms. It's server side is [ODK
Central](https://docs.getodk.org/central-intro/), which replaces the 
older [ODK Aggregate](https://docs.getodk.org/aggregate-intro/). ODK
Central manages the XLSForms downloaded to your phone, as wall as the
submissions uploaded from your phone when back online.

A related project for processing ODK data and working remotely with
Central is [osm-fieldwork](https://hotosm.github.io/osm-fieldwork/).
This Python project handles conversion of the various data files from
Collect or Central, into OSM XML and GeoJson for future processing via
editing or conflation. This is heavily used in the FMTM backend.

## Field Data Collection
  
Collecting data in the field is to best way to add data to
OpenStreetMap. Whether done by casual mappers adding POIs, to more
dedicated mappers, what is reality at that moment is the key to
keeping OSM fresh and updated. When it comes to improving the metadata
for buildings, many have been imported with **building=yes** from remote
mapping using the [HOT Tasking Manager](https://tasks.hotosm.org/) to
trace buildings from satellite imagery. 

But ground-truthing what kind of building it is improvers the map. It
may be a medical clinic, restaurant, residence, etc.. who know until
somebody stands in front of the building to collect more informsation
about it. This may be idenifying it as a clinic or reseidence, adding
the building material, what is the roof made of, is it's power
non-existance, or are there solar panels or a generator ? Some
humanitarian mapping is collecting data on public toilets, and
community water sources for future improvements. 

Knowing there is a building on the map is useful, but better yet is
what is the building used for ? What is it made of ? Does it have AC
or DC power ? Water available ? All of these details improve the map
to make it more useful to others.

### Field Mapping Tasking Manager

The [Field Mapping Tasking Manager](https://fmtm.hotosm.org) (FMTM) is a
project to oprganize large scale data collection using ODK Collect and
ODK Central. It uses the osm-fieldwork project for much of the backend
processing of the ODK data,  but is designed for large scale field
mapping involving many people. It uses ODK Collect and ODK Central as
the primary tools. One of the final steps in processing ODK data to
import into OSM is conflating it with existing data. This can be done
manually of course, but with a large number of data submissions this
becomes tedious and time consuming. FMTM aggrgates all the data for an
entire project, and may have thousands of submissions. This is where
conflation is critical.

# The Algorythm

Currently conflation is focused on ODK with OSM. This uses the
conflator.py program which can conflate between the ODK data and an
OSM data extract. There are other conflation programs in this project
for other external datasets, but uses a postgres database instead of
two files.

## The Conflator() Class

This is the primary interface for conflating files. It has two primary
endpoint. This top level endpoint is **Conflator.conflateFiles()**,
which is used when the conflator program is run standalone. It opens
the two disk files, parses the various formats, and generates a data
structure used for conflation. This class uses the **Parsers()** class
from osm-fieldwork that can parse the JSON or CSV files downloaded
from ODK Central, or the ODK XML "instance" files when working
offline. OPSM XML or GeoJson files are also supported. Each entry in
the files is turned into list of python dicts to make it easier to
compaert the data.

Once the two files are read, the **Conflator.conflateFeatures()**
endpoint takes the two lists of data and does the actual
conflation. There is an additional parameter passed to this endpoint
that is the threshold distance. This is used to find all features in
the OSM data extract within that distance. Note that this is a unit of
the earth's circumforance, not meters, so distance calulations are a
bit fuzzy.

This is a brute force conflation algorythm, not fast but it tries to
be complete. it is comprised of two loops. The top level loops through
the ODK data. For each ODK data entry, it finds all the OSM features
within that threshold distance. The inner loop then uses the closest
feature and compares the tags. This is where things get
interesting.... If there is a *name* tag in the ODK data, this is
string compared with the name in the closest OSM feature. Fuzzy string
matching is used to handle minor spelling differences. Sometimes the
mis-spelling is in the OSM data, but often when entering names of
features on your smartphone, mis-typing occurs. If there is a 100%
match in the name tags, then chances are the feature exists in OSM
already.

If there is no *name* tag in the ODK data, then the other tags are
compared to try to find a possible duplicate feature. For example, a
public toilet at a trailhead has no name, but if both ODK and OSM have
**amenity=toilet**, then it's very likey a duplicate. If no tags
match, then the ODK data is proably a new feature.

Any time a possible duplicate is found, it is not automatically
merged. Instead a **fixme** tag is added to the feature in the output
file with a statement that it is potentially a duplicate. When the
output file is loaded into JOSM, you can search for this tag to
manually decide if it is a duplicate.

## XLSForm Design

Part of the key detail to improve conflation requires a carefully
created XLSForm. There is much more detailed information on
[XLSForm design](xlsforms.md), but briefly whatever is in the *name*
column in the *survey* sheet becomes the name of the tags, and
whatever is in the *name* column in the *choices* sheet becomes the
value. If you want a relatively smooth conflation, make sure your
XLSForm uses OSM tagging schemas.

If you don't follow OSM tagging, then conflation will assumme all your
ODK data is a new feature, and you'll have to manually conflate the
results using JOSM. That's OK for small datasets, but quickly becomes
very tedious for the larger datasets that FMTM collects.

## The Output File

The output file must be in OSM XML to enable updating the ways. If the
OSM data is a POI, viewing it in JOSM is easy. If the OSM data is a
polygon, when loaded into JOSM, they won't appear at first. Since the
OSM way created by conflation has preserved the *refs* used by OSM XML
to reference the nodes, doing *update modified* in JOSM then pulls
down the nodes and all the polygons will appear.

## Conflicts

There are some interesting issues to fix post conflation. ODK data is
usually a single POI, whereas in OSM it may be a polygon. Sometimes
though the POI is already in OSM. Remote mapping or building footprint
imports often have a polygon with a single **building=yes** tag. If
the POI we collected in ODK has more data, for example this building is
a restaurant serving pizza, and is made of brick.

In OSM sometimes there is a POI for an amenity, as well as a building
polygon that were added at different times by different people.  The
key detail for conflation is do any of the tags and values from the
new data match existing data ?

FMTM downloads a data extract from OSM using
[osm-rawdata](https://hotosm.github.io/osm-rawdata/), and then
filters the data extract based on what is on the choices
sheet of the XLSForm. Otherwise Collect won't launch. Because this
data extract does not contain all the tags that are in OSM, it creates
conflicts. This problem is FMTM specific, and can be improved by
making more complete data extract from OSM.

When the only tag in the OSM data is **building=**, any tags from ODK
are merged with the building polygon when possible. If the OSM feature
has other tags, JOSM will flag this as a conflict. Then you have to
manually merge the tags in JOSM.
