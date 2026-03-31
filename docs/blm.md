# BLM Dataset

There are often BLM public lands mixed with Forest lands, and out west
large areas of BLM lands.

For example, these are some of the [ abbreviations
list](abbreviations.md) I've found while converting metadata.

* ROUTE_PRIMARY_NM becomes **name**
* ROUTE_PRMRY_NM becomes **name**
* ROUTE_PLAN_ID becomes **ref**

## OBSRVE_ROUTE_USE_CLASS becomes
* 2WD Low becomes **4wd_only**=*yes*
* 4WD High Clearance/Specialized becomes **4wd_only**=*yes*
* 4WD Low becomes **4wd_only**=*yes*
* 4wd High Clearance / Specialized becomes **4wd_only**=*yes*
* 4wd Low becomes **4wd_only**=*yes*
* ATV becomes **atv**=*designated*
* Impassable becomes **smothness**=*impassable*
* Motorized Single Track becomes **motorcycle**=*designated*
* Over Snow Vehicle becomes **snowmobile**=*designated*
* Trail - Non Motorized becomes **hiking**=*designated*
* UTV becomes **atv**=*designated*

## PLAN_ALLOW_MODE_TRNSPRT becomes

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

## - SNOW_NON_MECH_SHARED or SNOW_NON_MOTO_SHARED become
  * TECH_HI_CLEAR_VEH_ONLY becomes **4wd_only**=*yes*
  * Tech_Hi_Clear_VEH_ONLY becomes **4wd_only**=*yes*

## PLAN_MODE_TRNSPRT becomes
  * Motorized becomes ****motor_vehicle****=**designated*
  * Non-Mechanized becomes ****motor_vehicle**=*no*

## OBSRVE_ROUTE_USE_CLASS becomes
  * ATV becomes **atv**=*designated*
  * UTV becomes **utv**=*designated*
  * Over Snow Vehicle becomes **snowmobile**=*designated*
  * Motorized Single Track becomes **motocycle**=*designated*
  * 4WD Low becomes **4wd_only**=*yes*
  * 4wd High Clearance becomes **4wd_only**=*yes*
  * Primitive Road becomes **4wd_only**=*yes*
  * Impassable becomes **smoothness**=*horrible*
  * 4WD High Clearance/Specialized becomes **4wd_only**=*yes*

## PLAN_ROUTE_DSGNTN_AUTH becomes
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
