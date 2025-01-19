# local-roads.py

This program processes some state highway data. It will convert the
dataset to using OSM tagging schema so it can be
conflated. Abbreviations are discouraged in OSM, so they are
expanded. Most entries in the dataset fields are ignored. There often
isn't much here beyond state and county highway names, but it is
another dataset to validate highway names and State and county
reference numbers.

	This program converts local highway data into an OSM schema.

	options:
	-h, --help            show this help message and exit
	-v, --verbose         verbose output
	-i, --infile INFILE   Output file from the conflation
	-c, --convert         Convert highway feature to OSM
	-o, --outfile OUTFILE
  
