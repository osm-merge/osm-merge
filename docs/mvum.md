# MVUM & RoadCore Conversion

The MVUM and RoadCore datasets are all of the motor vehicle roads in a
national forest. These are primarily remote dirt roads, often just a
jeep track. These are heavily used for back country access for
wildland fires and rescues. Currently much of this data has been
imported in the past, complete with all the bugs in the dataset. The
RoadCore dataset is a superset of the MVUM data, but otherwise the
same. Since OpenStreetMap contains more than jeep tracks, the
RoadCore dataset is usually used for conflation.

This utility program normalizes the data, correcting or flagging bugs
as an aid for better conflation. It can process both the MVUM and
RoadCore datasets.. The schema between these two is the same other
than a subtle difference in field names.

The original datasets can be found here on the USDA 
[FSGeodata
Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation) website.

## Dataset Bugs

No dataset is bug free. This includes all the external datasets and
OSM as well. To avoid creating new bugs, each feature must be
validated carefully.

### Bad Geometry

There are many instances where a highway in the MVUM or RoadCore data
is a MultiLineString instead of just a LineString. The problem with
these are sometimes the segments are far apart, with long sections
with no data. These are all the same highway, just bad data. To me it
looks like somebodies's GPS had a dropped signal in places when they
were recording a track.

### Bad Reference Numbers

Every national foreset has it's own schema for reference
numbers. There is some similarity between them all, but sometimes it's
hard to tell the difference between a bad reference number, and a
local numbering scheme. Having stared at much data, my guess is
sometimes a prefix represents something like a trail vs a road. As I
work my way through each forest, I'll try to document what appears to
be a local numbering scheme.

In some areas the MVUM and RoadCore data has extract numerals prefixed
to the actual reference number. These are all usually in the same
area, so I assume whomever was doing data entry had a sticky keyboard,
it got messed up when converting from paper maps to digital, who
really knows. But it makes that tag worthless. Utah datasets in
particular suffer greatly from this problem.

Another common problem in the reference nummbers is in some areas the
major maintained roads have a *.1* appended. All minor part of the
number should always have a letter appended. So *FR 432.1" is actually
*FR 432", whereas "432.1A* is correct. This was confirmed by reviewing
multiple other map sources, as the paper and PDF version of the
dataset has the correct version without the .1 appended. Obviously
this dataset is not used to produce the maps you can get from the
Forest Service.

Cleaning up all the wrong reference numbers will make OSM the best map
for road and trail navigation on public lands.

### Doesn't Match The Sign

There is an issue with the USFS reference numbers not matching the
sign. This is luckily limited to whether there is a *.1* appended to
the reference number without an letter at the end. Usually a reference
without a *.1* is a primary road, and the *.1* gets appended for a
major branch off that road. While out ground-truthing MVUM roads
recently I saw multiple examples where the reference numnber in the
MVUM data (and often in OSM) has the *.1*, so I use that value
regardless of what the sign says. It's still quite obviously what the
reference number is since the only difference is the *.1* suffix.

This gets more interesting when you compare with other data sources,
ie... paper and digital maps. Older data source seem to drop the *.1*,
whereas the same road in a newer version of the dataset has the *.1*
suffix. So I figure anyone navigating remote roads that checks their
other maps would figure out which way to go. So anyway, when way out
on remote *very_bad* or *horrible* MVUM roads, you should have
multiple maps if you don't want to get confused.

### Missing Geometry

There are features with no geometry at all, but the tags all match an
existing feature that does have a geometry. These appear to be
accidental duplicates, so they get removed.

### Dropped Fields

These fields are dropped as they aren't useful for OpenStreetMap.

* TE_CN
* BMP
* EMP
* SYMBOL_CODE
* SEG_LENGTH
* JURISDICTION
* SYSTEM
* ROUTE_STATUS
* OBJECTIVE_MAINT_LEVEL
* FUNCTIONAL_CLASS
* LANES
* COUNTY
* CONGRESSIONAL_DISTRICT
* ADMIN_ORG
* SERVICE_LIFE
* LEVEL_OF_SERVICE
* PFSR_CLASSIFICATION
* MANAGING_ORG
* LOC_ERROR
* GIS_MILES
* SECURITY_ID
* OPENFORUSETO
* IVM_SYMBOL
* GLOBALID
* SHAPE_Length

### Preserved Fields

The field names are a bit truncated in the dataset, but these are the
ones that are converted. The MVU and RoaCore datasets uses the same
columns names, the only difference is whether an underbar is used.

* ID is id
* NAME is name
* OPER_MAINT_LEVEL is smoothness
* SYMBOL_NAME smoothness
* SURFACE_TYPE is surface
* SEASONAL is seasonal
* PRIMARY_MAINTAINER is operator

## Abbreviations

There are multiple and somewhat inconsistent abbreviations in the MVUM
dataset highway names. OpenStreetMap should be using the full
value. These were all found by the conflation software when trying to
match names between two features. Since much of the MVUM data is of
varying quality, there's probably a few not captured here that will
have to be fixed when editing the data. This however improves the
conflation results to limit manual editing.

* " Cr " is " Creek "
* " Cr. " is " Creek "
* " Crk " is " Creek "
* " Cg " is " Campground "
* " Rd. " is " Road"
* " Mt " is " Mountain"
* " Mtn " is " Mountain"
* " Disp " is " Dispersed"
* " Rd. " is " Road"
* " Mtn. " is " Mountain"
* " Mtn " is " Mountain"
* " Lk " is " Lake"
* " Resvr " is " Reservoir"
* " Spg " is " Spring"
* " Br " is " Bridge"
* " N " is " North"
* " W " is " West"
* " E " is " East"
* " S " is " South"
* " So " is " South"

# Tag values

## OPER_MAINT_LEVEL

This field is used to determine the smoothness of
the highway. Using the official forest service guidelines for this
field, convienently they publish a [Road Maintaince
Guidelines](https://www.fs.usda.gov/Internet/FSE_DOCUMENTS/stelprd3793545.pdf),
complete with muiltiple pictures and detaild technical information on
each level. The coorelate these values, I did some ground-truthing on
MVUM and I'd agree that *level 2* is definetely high clearance
vehicle only, and that it fits the [definition
here](https://wiki.openstreetmap.org/wiki/Key:smoothness) for
**very_bad**, although some sections were more **horrible**, deeply
rutted, big rocks, lots of erosion.

* 5 -HIGH DEGREE OF USER COMFORT: 
Assigned to roads that provide a high degree of user comfort and
convenience. This becomes **smoothness=excellent**.

* 4 -MODERATE DEGREE OF USER COMFORT: 
Assigned to roads that provide a moderate degree of user comfort and
convenience at moderate travel speeds. This becomes
**smoothness=bad**.

* 3 -SUITABLE FOR PASSENGER CARS: 
Assigned to roads open for and maintained for travel by a prudent
driver in a standard passenger car. This becomes **smnoothness=good**.

* 2 -HIGH CLEARANCE VEHICLES: 
Assigned to roads open for use by high clearance vehicles.
This adds **4wd_only=yes** and becomes **smoothness=vary_bad**.

* 1 -BASIC CUSTODIAL CARE (CLOSED): 
Assigned to roads that have been placed in storage (&gt; one year)
between intermittent uses. Basic custodial maintenance is
performed. Road is closed to vehicular traffic. This becomes
**access=no**

## SYMBOL_NAME

Sometimes *OPER_MAINT_LEVEL* doesn't have a value, so this is used as
a backup. These values are not used to update the existing values in
OSM, they are only used for route planning ground-truthing trips.

* Gravel Road, Suitable for Passenger Car becomes *surface=gravel*
* Dirt Road, Suitable for Passenger Car becomes *surface=dirt*
* Road, Not Maintained for Passenger Car becomes *smoothness=very_bad*
* Paved Road becomes *surface=paved*

## SURFACE_TYPE

This is another field that is converted, but not used when editing the
existing OSM feature. This can only really be determined by
ground-truthing, but it converted as another aid for route planning.

* AGG -CRUSHED AGGREGATE OR GRAVEL becomes *surface=gravel*
* AC -ASPHALT becomes *surface=asphalt*
* IMP -IMPROVED NATIVE MATERIAL becomes *surface=compacted*
* CSOIL -COMPACTED SOIL becomes *surface=compacted*
* NAT -NATIVE MATERIAL becomes *surface=dirt*
* P - PAVED becomes *surface=paved*

## Name

The name is always in all capitol letters, so this is converted to a
standard first letter of every word is upper case, the rest is lower
case.

## Options

	-h, --help            show this help message and exit
	-v, --verbose         verbose output
	-i INFILE, --infile INFILE MVUM data file
	-c, --convert         Convert MVUM feature to OSM feature
	-o OUTFILE, --outfile OUTFILE Output GeoJson file

