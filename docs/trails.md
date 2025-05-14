# National Park Service Trails

This processes both the National Park Service trails dataset, and the
National Forest Service trail datasets. The schema of the two datasets
is very similar. One of the differences is for Park Service Trails has
two default tags in the output file which are *bicycle=no* and
*motor_vehicle=no*. These default tags are [documented
here](https://wiki.openstreetmap.org/wiki/US_National_Park_Service_Tagging:_Trails).

This dataset is available in a variety of formats from the [ArcGIS Hub](https://hub.arcgis.com/datasets/fedmaps::national-park-service-trails/about).

## Processed Fields

These are the fields extracted from the data that are converted to
OpenStreetMap syntax so they can be conflated.

* OBJECTID becomes **id**
* TRLNAME becomes **name**
* TRLALTNAME becomes **alt_name**
* MAINTAINER becomes **operator** (although seems to only be the NPS)
* TRLUSE becomes *yes* for **horse**, **bicycle**, **atv**, etc...
* SEASONAL becomes **seasonal**
* TRLSURFACE becomes **surface**

### TRLUSE

This is a messy tag with multiple possible values, each seperated by a
vertical bar. Some values use a slash when the values may be similar,
for example __Hiker/Biker/Pedestrian__, which for OSM will have only
one value, *foot=yes*. There's also many variations on the values, but
they do fall into the same group. When seen in the data, these values
are converted into *="yes"* instead of *designated*. The values that
refer to motorized access use *highway=track* instead of
*highway=path*.

* Hiker, Pedestrian, Hike, Walking, Hiking becomes **foot=**
* Bike, Biker, Biking, Bicycle becomes **bicycle=**
* Horse, Horseback, Pack Or Saddle, Equestrian: becomes **horse=**
* Snowshoe becomes **snowhoe=**
* Cross-Country Ski becomes **ski=nordic**
* Dog Sled becomes **dog_sled=**, but isn't a common OSM tag
* Trail/Admin Road becomes **highway=service**
* Wheelchair Accessible Trail becomes **wheelchair=**
* Watercraft becomes **boat=**
* Motorized Watercraft becomes **motorboat=**
* Non Motorized Watercraft becomes **boat=**
* Motorized becomes **motor_vehicle=**
* Motorcycle becomes **morotcycle=**
* All-Terrain Vehicle becomes **atv=**
* Snowmobile becomes **snowmobile=**

### TRLSURFACE

This is another data field with multiple possible values, sometimes
lower case, other times uppercase, so case insensitive string matching
is used. These map directly to thwir OSM equivalant. There are some
other weird values, but they are ignored as we only want to convert a
data field when it has an OSM equivalant.

* Asphalt
* Bituminous
* Earth
* Grass
* Gravel
* Concrete
* Native
* Wood
* Snow
* Water
* Sand
* Stone
* Dirt

## Dropped Fields

These fields are all ignored, and are dropped from the output file.

* MAPLABEL
* TRLSTATUS
* TRLTYPE
* TRLCLASS
* PUBLICDISP
* DATAACCESS
* ACCESSNOTE
* ORIGINATOR
* UNITCODE
* UNITNAME
* UNITTYPE
* GROUPCODE
* GROUPNAME
* REGIONCODE
* CREATEDATE
* EDITDATE
* LINETYPE
* MAPMETHOD
* MAPSOURCE
* SOURCEDATE
* XYACCURACY
* GEOMETRYID
* FEATUREID
* FACLOCID
* FACASSETID
* IMLOCID
* OBSERVABLE
* ISEXTANT
* OPENTOPUBL
* ALTLANGNAM
* ALTLANG
* NOTES

## National Forest Service Trails

The US Forest Service makes much of their data publically accessible,
so it's been a source for imports for a long time. There is a nice
detailed wiki page on the [Forest Service
Data](https://wiki.openstreetmap.org/wiki/US_Forest_Service_Data). The
conversion process handles most of the implementation details.

# Kept Fields

The two primary fields are *TRAIL_NO*, which is used for the
*ref:usfs* tags, and *TRAIL_NAME*, which is the name of the trail. In
addition to these

## The 5 Variations

For many of the features classes, there are 5 variations on each one
which is used for access.

* Managed: Usage allowed and managed by the forest service
* Accepted: Usage is accepted year round
* Accepted/Discouraged: Usage is accepted, but discouraged
* Restricted: Usage is restricted
* Discouraged: Usage is discouraged

These are converted to the apppropriate value, but most are not in the
output file as they don't really have an OSM equivalent. For a value,
these use a date string, which becomes **opening_hours** in OSM. The
prefix which is *HIKER*_, *ATV_*, etc... becomes the access tag,
similar to the NPS values. For USFS trails, the values *designated**
is used instead of *yes*.

* Managed*  could set keyword to **designated**
* Accepted* could set the keyword to **yes**
* Discouraged* could set the keyword to **discouraged**
* Accepted/Discouraged* could set the keyword to **permissive**
* Restricted* sets the keyword to **no**

Many of the values for these are NULL, so ignored when generating the
output file. If the value exists.

* PACK_SADDLE_ becomes **horse=**
* BICYCLE_ becomes **bicycle=**
* MOTORCYCLE_ becomes **motorcycle=**
* ATV_ becoms **atv=**
* FOURWD_ becomes **4wd_only**
* SNOWMOBILE_ becomes **snowmobile=**
* SNOWSHOE_ becomes **snowwhoe=**
* XCOUNTRY_SKI_ becomes **ski=**
* HIKER_PEDESTRIAN becomes **foot=**, but is the default, so not needed
* MOTOR_WATERCRAFT becomes **motorboat=**
* NONMOTOR_WATERCRAFT becomes **boat**

Currently these fields appear to be empty, but that may change in the
future.

* SNOWCOACH_SNOWCAT_
* SNOWCOACH_SNOWCAT_
* E_BIKE_CLASS1_
* E_BIKE_CLASS2_
* E_BIKE_CLASS3_

## Dropped Fields

These fields are dropped as unnecessary for OSM. Most only have a
NULL value anyway, so useless.

* GIS_MILES
* Geometry Column
* TRAIL_TYPE
* TRAIL_CN
* BMP
* EMP
* SEGMENT_LENGTH
* ADMIN_ORG
* MANAGING_ORG
* SECURITY_ID
* ATTRIBUTESUBSET
* NATIONAL_TRAIL_DESIGNATION
* TRAIL_CLASS
* ACCESSIBILITY_STATUS
* TRAIL_SURFACE
* SURFACE_FIRMNESS
* TYPICAL_TRAIL_GRADE
* TYPICAL_TREAD_WIDTH
* MINIMUM_TRAIL_WIDTH
* TYPICAL_TREAD_CROSS_SLOPE
* SPECIAL_MGMT_AREA
* TERRA_BASE_SYMBOLOGY
* MVUM_SYMBOL
* TERRA_MOTORIZED
* SNOW_MOTORIZED
* WATER_MOTORIZED
* ALLOWED_TERRA_USE
* ALLOWED_SNOW_USE

## Options

	-h, --help            show this help message and exit
	-v, --verbose         verbose output
	-i INFILE, --infile INFILE input data file
	-c, --convert         Convert feature to OSM feature
	-o OUTFILE, --outfile OUTFILE Output GeoJson file

