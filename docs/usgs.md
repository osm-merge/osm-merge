# US Topographical Data

You can download the vector files for US topographical maps from the
USDA. The vector files are [available from
here.](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/),
which is maintained by the National Forest Service. There are 3
formats supported, I prefer the GeoPackage or GDB formats, as
Shapefiles truncate field names. It's easier to process the data with
the full field names. The data is in 7.5quad squares, so you have to
merge them togther if you want to work in larger areas. I use ogrmerge
to do this.

Note that they are in NAD83, so need to be converted to
NAD84 to fix the geometries. I use ogr2ogr to do this, Directions on how to do
this using QGIS are on the [OSM
Wiki](https://wiki.openstreetmap.org/wiki/How_to_transform_data_from_NAD83_to_WGS84). To
use ogr2ogr, this is the command line I use.

	ogr2ogr -progress -t_srs EPSG:4326 -s_srs EPSG:4269 [DEST] -makevalid [SRC]

## Useful Data For OpenStreetMap

The trail and highway (and other) features are all in the same
file. They have some overlap in data fields, but then extend that for
the two primary feature types we want. The trail data has access
information, atv, horses, etc...

# US Topographical Trails

* *name* which becomes __name__
* *trailnumber* which becomes _-ref__
* *primarytrailmaintainer* which becomes __operator__
* *hikerpedestrian* which becomes 
* *bicycle* which becomes 
* *packsaddle* which becomes 
* *atv* which becomes 
* *motorcycle* which becomes 
* *ohvover50inches* which becomes 
* *snowshoe* which becomes 
* *crosscountryski* which becomes 
* *motorcycle* which becomes 
* *ohvover50inches* which becomes 
* *snowshoe* which becomes 
* *crosscountryski* which becomes 
* *dogsled* which becomes 
* *snowmobile* which becomes 
* *nonmotorizedwatercraft* which becomes 
* *motorizedwatercraft* which becomes 
* *primarytrailmaintainer* which becomes 

### Ignored Data Fields

* loaddate
* permanentidentifier
* namealternate
* trailnumberalternate
* sourcefeatureid
* sourcedatasetid
* sourcedatadecscription
* sourceoriginator
* trailtype
* nationaltraildesignation
* lengthmiles
* networklength

## US Topographical Highways

* *name* which becomes __name__

I noticed in this dataset a big problem with the wrong names. The road
name I live on is a duplicate of a road name nearby, and the county
reference number is also missing. So any using this data should be
validated against other sources. Since the MVUM data has the
proper names and references, that should be considered the primary
source. I mostly wanted to scrape country roads references where I
can, and was curious what the data looked like.

* *us_route* which becomes __-ref="US XXX"__
* *state_route*  which becomes __-ref="CO XXX"__
* *county_route*  which becomes __-ref="CR XXX"__
* *federal_lands_route*  which becomes __-ref="FR XXX"__

Reference numbers are spread across multiple fields. Some highways may
have multiple reference numbers, county, forest service, BLM,
etc... These go in the *ref* tag in OSM seperated by a seni-colon (;).

### Ignored Data Fields

These fields are meaningless, so ignored.

* permanent_identifier
* source_featureid
* source_datasetid
* source_datadesc
* interstate
* stco_fipscode
* tnmfrc
* mtfcc_code

These are usually just NULL anyway, but on the rare occasions they do
have a value, it's a duplicate of one of the 4 fields we are
converting, so can be ignored.

* interstate_a
* interstate_b
* interstate_c
* us_route_a
* us_route_b
* us_route_c
* state_route_a
* state_route_b
* state_route_c

