# Extending to Other Datasets

This project is designed to be extensible for multiple external
datasets, not just the remote highways and trails I've been focused
on. There is some code duplicate between the conversion scripts to
reduce complexity. The idea is to add support for a different dataset
is to just copy an existing script and just modifiy it.

The conversion process generates good OpenStreetMap tagging to make
editing existing data, or for an import easier. To do this conversion
manually is ok a few times, but gets tedious if you do it multiple
times. The conversion scripts automate this process, so it's very easy
to run the script multiple times while editing the configuration file
till you get the output you want.

## The Configuration File

Each conversion script uses a text based configuration file in YAML
format. There are two main categories, __abbreviations** and
**tags**. These drive the entire conversion process. All map data
metadata is just a tag/value pair, the first column is the value in
the external dataset, and the second column is the value we want it to
change to.

Some values have additional criteria used when matching tags. For
example the access tag has multiple possible values when processing
trail data. Any value in the external dataset not in this list is
dropped from the output file.

	- access:
		- hiker: foot
		- pedestrian: foot
		- biker: bicycle
		- bicycle: bicycle
		- horse: bicycle
		- snowshoe: snowshoe

In this example, the **access** keyword is not in the external
dataset, it's generated internall. In the National Park Service trail
data there is the *TRLUSE* keyword, which we set to *access*. Later
when the conversion script sees the converteed value to *access*, it
then uses that list for the final value.

	- TRLUSE: access

### Abbreviations

OpenStreetMap prefers all abbreviations get expanded, and most
external datasets use the abbreviations. This saves much manual
editing if you want good OpenStreetMap syntax. Changing the list of
abbreviations is very easy. For an example, here's a short list of
common abbreviations.

	- abbreviations:
		- Fdr: FR
		- Cr: Creek
		- Crk: Creek
		- Cg: Campground
		- Th: Trailhead
		- Tr: Trail
		- Rd: Road
		- Rd: Road
		- Mt: Mountain 
		- Mtn: Mountain

When processing each feature that has a name, this iterates through
the string value and expands all the abbreviations. The large amount
of variety of abbreviations means not everything gets
expanded. Processing is relatively fast, so I just run the conversion
script multiple times and add the abbreviations that got missed to the
list in the configuration file till I catch everything. The few that
sslip through conversion can also be fixed manually when editing, but
the whole goal is to reduce manual editing of data.

There is an actual official list of abbreviations as used by the US
Postal Service, but obviosly nobody paid attention. Some of the
abbreviations have embedded spaces, periods, quote marks, etc... It
gets amusing after a while.

## The Conversion Script

The conversion scripts are where the final customization is for each
external dataset. While the configuration file handles most of the
details, each dataset usually has a few quirks to be worked
around. Most of the corrections are just filtering strings.

For example, the National Park Service trail data has 4 possible
values for each access type, and OpenStreetMap only needs one
value. In this case the conversion script has to search the string for
the unique value, use that, and ignore the others as they are usually
not set, or the same. It gets more interesting than that as each of
the possible values we want in OpenStreetMap may have multiple
values! The conversion script handles this by using the list in the
configuration file to looks for all possible values.

While it would possible to have all the values in the configuration
file, it adds much clutter, so handling it in the conversion script is
less bloated, and allows for more flexibility.

The existing conversion scripts are very flexible, and probably have
an example you can use for anything you are tryihng to process that's
a bit weird.

# Analysing External Datasets

This assumes you are using GeoJson format, which is supported by most
all GIS tools. I'm a terminal based developer, so these suggestions
are all command line based. You can ignore this section if you are
working with your own data.

I use *ogrinfo* to read the file. Ogrinfo puts every data field in
the external dataset on a separate line, making it easy to *grep* for
all the variations of tag values. Since there are multiple features
with the same value, I sort the output and then keep only unique
entries. To find all the variations I just do this:

	ogrinfo -ro -al [infile] | grep "TRLUSE" | sort | uniq 

This is also useful as it prints the schema used by the dataset and
the data type of each field. It also display the projection, which is
important as everything needs to be in NAD84 for the geometries to be
correct.

I do use QGIS and JOSM to visualize the data while working on
converting to something I can then use for conflation. Editing a
national dataset though is a bit sluggish, so I'll make a smaller
extract and use that for the initial debugging of the
conversion. Once I'm happen with processing the subset, then I'll run
the full dataset to catch all the edge conditions.
