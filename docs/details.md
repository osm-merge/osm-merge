# National Forest Details

This page collects details about the datasets for each national
forest, park, or wilderness area that I come across as I process
data. This is not an exhaustive list, sometimes there are occasional
weird edge cases.

There are several external datasets available, this document focuses
on the
[MVUM](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip)
and [RoadCore](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.RoadCore_FS.zip)
datasets. The RoadCore and MVUM datasets are the same other than
RoadCore also includes roads that aren't jeep tracks. Both of these
datasets have the same bugs, which I assume is from old data
conversion issues as some of this data is ancient. This documents the
bugs found in the datasets as more detail into the conversion and
conflation process.

The goal is being able to refer to a remote highway or trail without a
GPS. Long before the digital age, locals, forest rangers and staff,
fire fighters, etc... needed a way to convey a location. Hence USFS
reference numbers. And many have names either invented by locals or by
USFS staff a very long time ago. I really love the fun names on
obscure highways. Often these are based on a historical incident, like
*Burn Road* (it was 100 years ago), *Bad Stew Road*, *Broken Wheel
Road*, etc... While digging through lots of map data is very boring,
finding interesting highway names helps keep it amusing.

## Highway Classification

Most of these highways are only tagged with
__highway=unclassified__, or __highway=residential__, and were from
the TIGER data import a long time ago. __highway=residential__ is a
common problem with old
[TIGER](https://wiki.openstreetmap.org/wiki/TIGER_fixup) data. While
sometimes there are remote cabins that use these highways (I live on
one), so this could be correct, but not likely. These should probably be
__highway=track__, based on the MVUM dataset. It'd be possible to use
satellite imagery to look for buildings and fix this tag, but that's a
whole other project, so whatever the current value in OSM is preserved
in the conflated output.

## Fork Splitting

Sometimes when a remote highway is traced using satellite imagery,
when it comes to a fork in the road, the mapper traces the wrong
branch. Often the USFS reference number changes at every fork, so
breaking the highway LineString into segments and correcting the tags
for each branch is important. In JOSM this is easy as there is a
*Split Way* option. I select the node where the branches connect,
split the LineString, and then update the tags for each branch.

These often appear in the conflated output as the geometry is not a
good match.

## Bad Geometry

The conflation software deals with differences in geometry reasonably
well. For data that was imported, this is easy, as the geometry is
often identical. There are several major issues that generate features in
the output data that at first appear to be correct. As noted above,
inaccurately traced highways will be in the conflated output, even if
the tags for some of the segments match. These require manually editing
the LineString.

Another common problem is the traced highway may be way off the actual
geometry due to offsets in the imagery. And different imagery sources
have different offsets. Often these will be parallel to an existing
OSM feature, so do match, but may generate a false positive in the
conflated output.

The other issue is with incomplete or overly extended
LineStrings. Often in the official datasets a remote highway may be
a series of disconnected short strings, whereas in OSM the geometry is
complete. These do match well, but often in OSM the LineString goes a
very long way, whereas in the official data it's a very short
highway. From previous ground-truthing trips, this is often where the
road becomes a trail, potentially an unofficial trailhead. It will
often have the same reference number, so applying that to the longer
LineString is probably accurate. There may be a name change, for
example changing *Road* to *Trail*.

I usually split the LineString into segments using the official
dataset as a guide. Often the *surface* tag in OSM, if it exists, may
apply to both segments even if there is a big change in the
condition. Often at these locations the transition may be to a much
narrower highway, badly eroded and rocky, etc... Ground-truthing is
the only way to really know. Fixing the reference numbers at least
makes it easy to refer to a specific highway later when
ground-truthing. And sometimes there is great camping at these locations.

## Thunder Basin National Grasslands

This is managed as part of the Medicine Bow Routt National
Forest. There are almost no highway names in this entire area, just
the USFS reference numbers for most. This makes adding the reference
number is critical if you want to know where you are if you are
looking at the MVUM or Forest Service map. Otherwise all you have are
lines on a map.

Looking at satellite imagery, I notice that many of these highways go
to oil drilling sites, so should probably be *access=private* or
*access=permissive*. To determine that would require conflating the
other datasets like land ownership, Oil leases, etc... which is
outside the scope of this project. But it's still important to have
reference numbers for all these highways.

## Medicine Bow Routt National Forest

This forest is in both Colorado and Wyoming. The non grassland part of
this forest has reasonably good reference number data. The main subtle
difference is the signs and older maps are often lacking the __.1__
suffix which is in the official dataset. This does signify a side road
off a more major highway, but doesn't effect navigation unless you are
as long as you are aware of this issue. This is noticeable when
comparing digital maps with older USGS topographical maps or USFS
forest maps.

## Rio Grande National Forest

Often a road that branches off of a more major highway is a Spur, and
includes an alpha numberic. Often this is the same as the suffix, for
example *ref:usfs=FR 123.2B* the name might be *Black Forest Spur B*.
In this forest none of that applies. Spur roads do have different
reference numbers, but the name is the same on all of them. At least
that's how it is in the data. It'll take a ground-truthing trip to
really know.

## Dixie National Forest

In the current MVUM and RoadCore datasets for this national forest,
for some reason a *30, 31, 32, 33, 34* has been prefixed to many of
the IDs, making the reference numbers wrong. I noticed this while
ground-truthing, as none of the MVUM/RoadCore maps matched the street
signs causing navigation issues.

After staring at the original data file, I noticed these were all 5
characters long, and lacked a letter or a minor number
suffix. It's possible these are some kind of internal data type, I'm
still investigating that possibility. Limiting the trigger to just
the 5 character test seems to fix the majority of the problem. A
*note* is added to any feature where the __ref:usfs__ tag is changed
as an aid towards validation. But these then also need to be manually
validated with newer maps.

As older MVUM maps, USFS topomaps, GeoPDF's all have the same
incorrect reference, newer versions of these datasets have the
corrected version. Unfortunately the wrong version is in the
publicly available datasets. But at least OSM will have the
up-to-date and correct version.

## Manti-LaSal National Forest

In the current MVUM dataset for this national forest, for some reason
a *5* or *7* has been prefixed to many of the IDs, making the reference
numbers wrong.

## Fishlake National Forest

In the current MVUM dataset for this national forest, for some reason
a *4* or *40* has been prefixed to some of the IDs, making the
reference numbers wrong.

## Mount Hood National Forest

For some reason, some of the reference numbers have a __000__
appended, making the reference numbers wrong. This applies to paved
roads, not just remote jeep tracks.

