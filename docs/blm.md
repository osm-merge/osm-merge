# BLM Datasets

Out west there are large areas of BLM lands, sometimes mix or adjacent
to national forest land.

## Parsing name and ref

The name field may be overloaded with multiple values. Most commonly
used is a colon character. The part of the value before the colon is
the reference number, and the following part is the name. There are a
few roads and trails that have both a BLM name and a USFS name. These
use *USGS* as a delimiter, anything after this becomes the
*alt_name*. In this case the USFS alt_name should be validated against
USGS data.

Also all of the names are lacking the **Trail** or **Road** as part of
the name. OpenStreetMap prefers this as it's additional data on what
type of highway it is. When converting all the features that specify
motorized access is designated, then **Road** is appended to the name
during conversion, other **Trail** is appended. And of course to keep
things interesting occasionally Trail or Road is already in the name, so
you have to check to avoid duplicates.

### Road Maintenance

In Utah, the references numbers have either a **B** or a **D**
prefixed, which designates if the road is maintained by the county, or
the BLM. All of the roads with a **B** prefix are also in all the
official state datasets as well. Utah has many BLM roads all mixed with
private property. Whether a road designated as a county road is
actually maintained is hard to judge unless you go there and
ground-truth it.

### Expanding Abbreviations

All of the names have abbreviations and OpenStreetMap prefers these
get expanded. These are some of the [ abbreviations](abbreviations.md)
I've found while converting the name field. Capitalization is also
fixed when converting names.

* ROUTE_PRIMARY_NM becomes **name**
* ROUTE_PRMRY_NM becomes **name**
* ROUTE_PLAN_ID becomes **ref**

## Other Data Fields

There are many data fields shared across all the BLM datasets, often
these have no value at all, so are ignored.

### OBSRVE_ROUTE_USE_CLASS becomes

* 2WD Low becomes **4wd_only**=*yes*
* 4WD High Clearance/Specialized becomes **4wd_only**=*yes*
* 4WD Low becomes **4wd_only**=*yes*
* 4wd High Clearance / Specialized becomes **4wd_only**=*yes*
* 4wd Low becomes **4wd_only**=*yes*
* ATV becomes **atv**=*designated*
* Impassable becomes **smoothness**=*impassable*
* Motorized Single Track becomes **motorcycle**=*designated*
* Over Snow Vehicle becomes **snowmobile**=*designated*
* Trail - Non Motorized becomes **hiking**=*designated*
* UTV becomes **atv**=*designated*

### PLAN_ALLOW_MODE_TRNSPRT becomes

* HIK_ONLY becomes **hiking**=*designated*
* ALL_MOTO_VEH becomes **motor_vehicle**=*designated*
* BIKE_HIK_ONLY becomes **hiking**=*designated*, **bicycle**=*designated*
* BIKE_ONLY becomes **bicycle**=*designated*
* EQU_HIK_ONLY becomes **hiking**=*designated*, **horse**=*designated*
* EQU_ONLY becomes **horse**=*designated*
* MTC_ATV_ONLY becomes **atv**=*designated*, **motorcycle**=*designated*
* MTC_ATV_SHARED becomes **atv**=*designated*, **motorcycle**=*designated*
* MTC_ATV_UTV_ONLY becomes **atv**=*designated*, **motorcycle**=*designated*
* MTC_ATV_UTV_SHARED becomes **atv**=*designated*, **motorcycle**=*designated*
* MTC_ONLY becomes **motorcycle**=*designated*
* MTC_SHARED becomes **atv**=*designated*, **motorcycle**=*designated*
* SNOW_MOTO_ONLY becomes **snowmobile**=*designated*
* SNOW_MOTO_SHARED becomes **snowmobile**=*designate*d

### - SNOW_NON_MECH_SHARED or SNOW_NON_MOTO_SHARED become

* TECH_HI_CLEAR_VEH_ONLY becomes **4wd_only**=*yes*
* Tech_Hi_Clear_VEH_ONLY becomes **4wd_only**=*yes*

### PLAN_MODE_TRNSPRT becomes

* Motorized becomes ****motor_vehicle****=**designated*
* Non-Mechanized becomes ****motor_vehicle**=*no*

### OBSRVE_ROUTE_USE_CLASS becomes

* ATV becomes **atv**=*designated*
* UTV becomes **utv**=*designated*
* Over Snow Vehicle becomes **snowmobile**=*designated*
* Motorized Single Track becomes **motorcycle**=*designated*
* 4WD Low becomes **4wd_only**=*yes*
* 4wd High Clearance becomes **4wd_only**=*yes*
* Primitive Road becomes **4wd_only**=*yes*
* Impassable becomes **smoothness**=*horrible*
* 4WD High Clearance/Specialized becomes **4wd_only**=*yes*

### PLAN_ROUTE_DSGNTN_AUTH becomes

* BLM becomes **operator**=*Bureau Of Land Management*
* FS becomes **operator**=*Forest Service*
* NPS becomes **operator**=*National Park Service*
* FS becomes **operator**=*Forest Service*

### surface becomes

* Aggregate becomes **surface**=*paved*
* Natural becomes **surface**=*dirt*
* Gravel/Aggregate becomes **surface**=*gravel*
* Paved becomes **surface**=*paved*
* Solid becomes **surface**=*compacted*
* Snow becomes **surface**=*snow*
