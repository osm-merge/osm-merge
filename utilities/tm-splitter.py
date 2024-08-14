#!/bin/python3

# Copyright (c) 2022 Humanitarian OpenStreetMap Team
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     FMTM-Splitter is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with FMTM-Splitter.  If not, see <https:#www.gnu.org/licenses/>.
#


"""
Class and helper methods for task splitting when working with the HOT
Tasking Manager since our projects are larger than 5000km area it
supports.

"""

import argparse
import json
import logging
import sys
import os
from math import ceil

from pathlib import Path
# from tqdm import tqdm
# import tqdm.asyncio
import asyncio
from cpuinfo import get_cpu_info
from fmtm_splitter.splitter import split_by_square, FMTMSplitter
import geojson
import numpy as np
from geojson import Feature, FeatureCollection, GeoJSON
from shapely.geometry import Polygon, shape, LineString, MultiPolygon
from shapely.prepared import prep
from shapely.ops import split
from cpuinfo import get_cpu_info
import shapely
from functools import partial
from shapely.ops import transform
from osgeo import ogr
from codetiming import Timer
from osgeo import osr

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
# Try doubling the number of cores, since the CPU load is
# still reasonable.
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Shapely.distance doesn't like duplicate points
warnings.simplefilter(action='ignore', category=RuntimeWarning)

# def grid_bounds(geom,
#                 delta: float,
#                 ):
    
#     minx, miny, maxx, maxy = geom.bounds
#     nx = int((maxx - minx)/delta)
#     ny = int((maxy - miny)/delta)
#     gx, gy = np.linspace(minx,maxx,nx), np.linspace(miny,maxy,ny)
#     grid = []
#     for i in range(len(gx)-1):
#         for j in range(len(gy)-1):
#             poly_ij = Polygon([[gx[i],gy[j]],[gx[i],gy[j+1]],[gx[i+1],gy[j+1]],[gx[i+1],gy[j]]])
#             grid.append( poly_ij )
#     return grid

# def partition(geom, delta):
#     timer = Timer(text="partition() took {seconds:.0f}s")
#     timer.start()

#     prepared_geom = prep(geom)
#     grid = list(filter(prepared_geom.intersects, grid_bounds(geom, delta)))

#     timer.stop()
#     return grid

def ogrgrid(outputGridfn: str,
            extent: tuple,
            threshold: float,
            # outLayer: ogr.Layer,
            ):
    """
    Generate a task grid.
    https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-fishnet-grid
    
    """
    timer = Timer(text="ogrgrid() took {seconds:.0f}s")
    timer.start()

    # convert sys.argv to float
    xmin = extent[0]
    xmax = extent[1]
    ymin = extent[2]
    ymax = extent[3]
    gridWidth = float(threshold)
    gridHeight = gridWidth
    # get rows
    rows = ceil((ymax-ymin)/gridHeight)
    # get columns
    cols = ceil((xmax-xmin)/gridWidth)

    # start grid cell envelope
    ringXleftOrigin = xmin
    ringXrightOrigin = xmin + gridWidth
    ringYtopOrigin = ymax
    ringYbottomOrigin = ymax-gridHeight

    # create output file
    outDriver = ogr.GetDriverByName('GeoJson')
    if os.path.exists(outputGridfn):
        os.remove(outputGridfn)
    outDataSource = outDriver.CreateDataSource(outputGridfn)
    outLayer = outDataSource.CreateLayer(outputGridfn,geom_type=ogr.wkbPolygon )
    featureDefn = outLayer.GetLayerDefn()

    # create grid cells
    countcols = 0
    while countcols < cols:
        countcols += 1

        # reset envelope for rows
        ringYtop = ringYtopOrigin
        ringYbottom =ringYbottomOrigin
        countrows = 0

        while countrows < rows:
            countrows += 1
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            # add new geom to layer
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(poly)
            outLayer.CreateFeature(outFeature)
            outFeature = None

            # new envelope for next poly
            ringYtop = ringYtop - gridHeight
            ringYbottom = ringYbottom - gridHeight

        # new envelope for next poly
        ringXleftOrigin = ringXleftOrigin + gridWidth
        ringXrightOrigin = ringXrightOrigin + gridWidth

    # Save and close DataSources
    outDataSource = None

    timer.stop()
    return outLayer

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts boundaries from USDA datasets",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose output")
    parser.add_argument("-i", "--infile", required=True,
                        help="The input dataset")
    parser.add_argument("-g", "--grid", action="store_true",
                        help="Generate the task grid")
    parser.add_argument("-s", "--split", default=False, action="store_true",
                        help="Split Multipolygon")
    parser.add_argument("-o", "--outfile", default="output.geojson",
                        help="Output filename")
    parser.add_argument("-e", "--extract", default=False, help="Split Dataset with Multipolygon")
    parser.add_argument("-t", "--threshold", default=1.1,
                        help="Threshold")
    # parser.add_argument("-s", "--size", help="Grid size in kilometers")

    args = parser.parse_args()
    indata = None
    source = None
    path = Path(args.infile)

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)


    # The infile is either the the file to split, or the grid file.
    file = open(args.infile, "r")
    grid = geojson.load(file)
    
    # Split the large file of administrative boundaries into each
    # area so they can be used for clipping.
    if args.split:
        index = 0
        name = str()
        for feature in grid['features']:
            if "FORESTNAME" in feature["properties"]:
                name = feature["properties"]["FORESTNAME"].replace(' ', '_')
            else:
                name = f"{path.stem}_{index}"
                index += 1
                feature["properties"]["name"] = name
                feature["boundary"] = "administrative"
            file = open(f"{name}.geojson", 'w')
            geojson.dump(FeatureCollection([feature]), file)
            file.close()
    elif args.grid:
        log.info(f"Generating the grid may take a long time...")
        path = Path(args.outfile)
        #grid2 = partition(grid, float(1.1))
        driver = ogr.GetDriverByName("GeoJson")
        indata = driver.Open(args.infile, 0)
        inlayer = indata.GetLayer()
        indefn = inlayer.GetLayerDefn()
        extent = inlayer.GetExtent()

        memdrv = ogr.GetDriverByName("Memory")
        memdata = memdrv.CreateDataSource(f"mem")
        # memlayer = memdata.CreateLayer("tasks", geom_type=ogr.wkbPolygon)
        ogrgrid(args.outfile, extent, args.threshold)

        fodata = driver.Open("bar.geojson", 0)
        folayer = indata.GetLayer()

        outfile = f"{path.stem}_grid.geojson"
        outdata = driver.CreateDataSource(outfile)
        if os.path.exists(outfile):
            os.remove(outfile)
        outlayer = outdata.CreateLayer("tasks", geom_type=ogr.wkbMultiPolygon)

        boundary = inlayer.GetNextFeature()
        poly = boundary.GetGeometryRef()

        index = 0
        # 1 meters is this factor in degrees
        meter = 0.0000114

        for poly in folayer:
            geom = poly.GetGeometryRef()
            for i in range(0, geom.GetGeometryCount()):
                task = geom.GetGeometryRef(i)
                area = task.GetArea() * meter
                log.debug(f"Area is: {area/1000}")
                memlayer = memdata.CreateLayer("tasks", geom_type=ogr.wkbPolygon)
                outfile = f"foobar_{index}.geojson"
                if os.path.exists(outfile):
                    os.remove(outfile)
                outdata = driver.CreateDataSource(outfile)
                outlayer = outdata.CreateLayer("tasks", geom_type=ogr.wkbPolygon)
                outFeature = ogr.Feature(indefn)
                outFeature.SetGeometry(task)
                memlayer.CreateFeature(outFeature)
                inlayer.Clip(memlayer, outlayer)
                outdata.Destroy()
                index += 1
            #for feature in result:
            #    outlayer.CreateFeature(feature)
        # if args.extract:
        #     grid = split_by_square(grid, meters=args.threshold, outfile=args.outfile, osm_extract=args.extract)
        # else:
        #     grid = split_by_square(grid, meters=args.threshold, outfile=args.outfile)
            log.info(f"Wrote {args.outfile}")

    if args.extract:
        # Use gdal, as it was actually easier than geopandas or pyclir
        driver = ogr.GetDriverByName("GeoJson")
        indata = driver.Open(args.infile, 0)
        inlayer = indata.GetLayer()
        indefn = inlayer.GetLayerDefn()
        logging.debug(f"Input File{inlayer.GetFeatureCount()} features before filtering")

        extdata = driver.Open(args.extract, 0)
        extlayer = extdata.GetLayer()
        extdefn = extlayer.GetLayerDefn()
        logging.debug(f"External dataset {extlayer.GetFeatureCount()} features before filtering")

        index = 0
        for task in inlayer:
            extlayer.SetSpatialFilter(task.GetGeometryRef())
            if extlayer.GetFeatureCount() == 0:
                # logging.debug("Data is empty!!")
                continue
            outdata = driver.CreateDataSource(f"{path.stem}_{index}.geojson")
            outlayer = outdata.CreateLayer("tasks", geom_type=ogr.wkbMultiLineString)
            for feature in extlayer:
                outlayer.CreateFeature(feature)
            #outlayer.Destroy()
            
            index += 1

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())