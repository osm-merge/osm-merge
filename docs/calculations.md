# Conflation Calculations

Part of the fun of external datasets, especially some that have been
around long time like the MVUM data is the the variety of
inconsistencies in the data. While OpenStreetMap itself is a bit
overly flexible at time, so is external data. And some of the old data
has been converted from other formats several times, with bugs getting
introduced each time.

## Geometries

OpenStreetMap has relations, which are a collection of references to
other features. External data may have LineStrings, MultiLineStrings
or a GeometryCollection, all in the same file! For all calculations
the MultiLineString and GeometryCollections are taken apart, so the
calculations are between OSM data and that segment of the external
data. Since this may product multiple values, those need to be
evaluated and the most likely one returned.

It gets more fun as sometimes the MVUM dataset is missing entire
segments. Course sometimes OSM is too. conflation successfully merges
the MVUM dataset tags for the segments if they match onto the single
OSM way.

![Screenshot\ from\ 2024-10-19\ 14-06-00.png])

## Distance

A simple distance calculation is performed after transforming the
coordinate system from global degrees to meters. The result is
compared to a threshold distance, and any feature within that
threshold is added to a list of possible matches. After a few features
are found in the required distance, matching stops and then the next
feature to be conflated is started on the same process.

If the highway is a GeometryCollection or MultiLineString, then it's
split into segments, and each one is checked for distance. The closest
one is what is returned.

## Slope and Angle

Distance often will return features that are close to each other, but
often they are spur roads off the more major one. So when two highway
segments are found close to each other, the angle between them is
calculated. This works well to differentiate between the more major
highway, and the spur road that splits off from that.

If the highway is a GeometryCollection or MultiLineString, then it's
split into segments, and each one is checked for the angle. The
closest one is what is returned.

Sometimes the geometry of the feature in OSM was imported from the same
external dataset. At that point it's an exact match, so the distance,
the slope, and the angle will all be 0.0.

## Tag Checking

Once there is at least one candidate within the parameters of distance
and angle, then the tags are checked for matches. The tags we are
primarily interested in are name(s) and reference number(s) of each
MVUM road or trail. Some of the existing features in OpenStreetMap may
be inaccurate as to the proper name and reference. And of course each
feature may have an *alt_name* or both a *ref* and a *ref:usfs*. Due
to the wonders of inconsistent data, a fuzzy string comparison is
done. This handles most of the basic issues, like capitalization, one
or 2 characters difference, etc... Anything above the threshold is
considered a probably match, and increments a counter. This value is
included in the conflated results, and is often between 1-3.

The reference numbers between the two datasets is also compared. There
is often a reference number in OSM already, but no name. The external
dataset has the name, so we want to update OSM with that. In addition,
the external datasets often have access information. Seasonal access,
private land, or different types of vehicles which can be added to
OSM.

### Tag Merging

The conflation process for merging tags uses the concept of primary
and secondary datasets. The primary is considered to have the *true*
value for a highway or trail. For example, if the name in the two
datasets doesn't match, the secondary will then rename the current
value to *old_something*. The primary's version becomes the same. Some
with reference numbers.

Other tags from the primary can also be merged, overriding what is
currently in OSM. Once again, the old values are renamed, not
deleted. When validating in JOSM, you can see both versions and make a
final determination as to what is the correct value. Often it's just
spelling differences.

For all the features in OSM that only have a *highway=something* as a
tag, all the desired tags from the primary dataset are added.

For some tags like *surface* and *smoothness*, the value in OSM is
potentially more recent, so those are not updated. For any highway
feature lacking those tags, they get added.

Optionally the various access tags for *private*, *atv*, *horse*,
*motorcycle*, etc... are set in the post conflation dataset if they
have a value in the external dataset. 

### Highway Segments

This turns out to be the challenging part of highway conflation. In
any highway dataset a longer highway may be broken into
segments. These changing segments may be due to the surface changing,
speed limit changing. etc... and may be organized into a group of
some kind.

The fun starts when the segments used for the OSM highway aren't the
same as the segments in the external dataset's geometry. Often
in the external dataset there are no segments at all, just a long
LineString. In OSM the same highway may be broken into multiple
segments.

The algorithm for the geometry calculations tries to compare each
segment from the primary dataset (if there are any), with any highway
segment in the secondary dataset (probably OSM). Later when processing
all the possible segments of any highway close to the primary segment,
the name and reference numbers are checked, and if they match, the new
tags from the external dataset are applied to all the matching
segments in the secondary.

## Issues

Conflation is never 100% accurate due to the wonderful
um... "flexibility" of the datasets. Minor tweaks to the steering
parameters for the distance, angle, and fuzzy string matching can
produce slightly different results. I often run the same datasets with
different parameters looking for the best results.

## Evaluating The Results

### Debug Tags

Currently a few tags are added to each feature to aid in validating
and debugging the conflation process. These should obviously be
removed before uploading to OSM. They'll be removed at a future date
after more validation. These are:

* hits - The number of matching tags in a feature
* name_ratio - The ratio for name matching
* ref_ratio - The ratio for USFS reference number matching
* dist -  The distance between features
* angle - The angle between two features
* slope - The slope between two features

### Decision Matrix

Initially each feature in the primary data source is compared to each
feature in the secondary data source. The first step is the distance
calculation, eliminating everything outside the threshold
distance. Each feature from the secondary dataset within range is put
on a list of possible matches. The angle and slope between the
external feature and OSM is also checked.

After searching through all of the secondary data, any features are
found within the desired distance, slope and angle between the primary
and secondary datasets. They are added to a list of possible matches.
The slopes and angle is checked to identify branches off the highway
that often have a similar name and reference number.

If there are any features left in the secondary dataset, after the
spatial calculations, then the tags are checked for matches.

#### Name Matching

Names are compared with fuzzy logic. This handles minor spelling
differences. All names are converted to lowercase when being compared
so there are no problems with capitalization. The ratio from the fuzzy
matching is returned as a float, and is the *name_ratio* for name
matching, and  *ref_ratios* for  reference matching in the debug
logs. There is a lot of variety in names in most datasets.

#### Reference Matching

Reference matching is similar other than the prefix of the reference
number has to be taken into consideration. A *ref* might be a local
county road, so starts with a __CR __ then the number. State and
federal highways use a similar scheme. Since we're focused on remote
highways, those are left unchanged by conflation. For the OSM Merge
use case, the only prefix we care about are __FR __, or __FS __. The
ratio from the fuzzy matching is returned as a float, and is the 
*ref_ratio* in the debug tags.

#### Changing Tags

When cleaning up OSM features, sometimes the USFS reference number is
in the name tag. Often this uses various prefixes, but these can be
identified, and moved to the correct *ref:usfs* tag from the name
tag. Or the reference is in a *ref* tag, and the same change is made,
it's moved to the *ref:usfs* tag. This change helps the conflation
process when trying to match tags since this process is done by the
[MVUM conversion](mvum.md) script, instead of in the conflation
algorithm.

#### Issues

Conflation is rarely perfect. The biggest issue is due to large
differences in the length of the highway or multiple segments. This
fails to match by geometry within a reasonable distance. In this case
the primary dataset feature is considered a *new* feature, so winds
up in the new feature output file, instead of the conflated highways
output file.

#### Evaluating Possible Matches

This is the key to conflation, evaluating the debug values to
determine the most likely match. Each highway segment within the
desired distance is put on a list, along with the results of comparing
the tags. This is just a list of possible matches, which then needs to
have the statistics evaluated to determine the best match.

The primary values for conflation after geometry matching is comparing
the tags between the external dataset and OSM. Many of these remote
highways in OSM only have *highway=track*, whereas the external
dataset may have a name and reference number. If the highway segments
are reasonably similar, this generates a feature in the output data
with the tags from the external dataset. When there are tags in both
datasets for the same features, this is where things get interesting.

There are three tests made to each feature. The first test is to
compare the name tag between the primary and secondary features. This
is a fuzzy string match, usually any value over 85 is a good match
with some variation. The variation is usually spelling differences, or
*trail* vs *road* for the name of a highway segment. A match ratio of
100 is of course a solid match.

The other two tests are for the USFS reference number. The reference
numbers have two parts, the prefix and the number. The number is an
alphanumeric, and may also include a period. In OSM data, the prefix
is usually __FS__ or __FR__, but often other wild variations like
__Nsfr__. The prefix is compared, and the number is compared without
the prefix. If the number matches, it's considered a probable hit even
if the prefix differs. a *hit* is a rough guess as to the confidence
the two features match.

If there is a match of the name or reference number, the *hits* value
gets set to __1__. To determine what was matched, it's possible to
look at the additional values of __name_ratio__ and __ref_ratio__,
which are returned from tag checking. Since there is likely additional
metadata in the external dataset, those tags are then merged with the
OSM ones.

If both the tags and the reference number match, the *hits* gets set
to __2__. The tags __name_ratio__ and __ref_ratio__ are still set, so
can be used to evaluate whether to trust the name or the reference
match the possible match more, since it's a fuzzy string match. Often
the reference number match is slightly off as in OSM some features use
*ref=FS 123*, where *ref=FR 123* is preferred. The reference number
itself, without the prefix is also checked. This then goes in the
output file to change to the preferred prefix for USFS highways.

If *hits* is set to __3__, then the name, the reference number prefix
and the reference prefix all match 100%, so this feature is not put in
the output file as no updates need to be made. Often when the number
match isn't 100% (hits == 2), it's because OSM has *FR 123*, and the
external dataset has *FR 123.1* or *FR 123A*, or *FS 123*. OSM Merge
changes the prefix from *FS* to FR* when it's used to make searching
the data more consistent when using mobile apps.

Since each highway be a segment of the entire feature, if there is a
good match with the name, then any other of the possible features
with that name gets the same metadata.
