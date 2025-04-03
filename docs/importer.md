# importer.py

Import data into a postgres database that is using the Uunderpass
schema. Currenly only loading Parquet files from Overture is
supported.

## Example

    importer.py -u localhost/overture -i 20230725_211555_00082_tpd52_545781f2-efb6-4ea2-a9a0-b91ec5451b73

    options:
    -h, --help                 show this help message and exit
    -v, --verbose              verbose output
    -i INFILE, --infile INFILE Input data file
    -u URI, --uri URI          Database URI

        This should only be run standalone for debugging purposes.
