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

### Debug Tags

Currently a few tags are added to each feature to aid in validating
and debugging the conflation process. These should obviously be
removed before uploading to OSM. They'll be removed at a future date
after more validation. These are:

* hits - The number of matching tags in a feature
* ratio - The ratio for name matching if not 100%
* dist -  The distance between features
* angle - The angle between two features
* slope - The slope between two features

## Issues

Conflation is never 100% accurate due to the wonderful
um... "flexibility" of the datasets. Minor tweaks to the steering
parameters for the distance, angle, and fuzzy string matching can
produce slightly different results. I often run the same datasets with
different parameters looking for the best results.

