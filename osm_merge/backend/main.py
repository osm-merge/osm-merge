#!/usr/bin/python3

# Copyright (c) 2026 OpenStreetMap US
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Form, APIRouter, Query
from shapely.geometry import Polygon, MultiPolygon
from starlette.responses import FileResponse
from osm_merge.utilities.egress import RouteAddrs
from typing import Annotated
from shapely.geometry import LineString, shape, Polygon, Point, MultiLineString, MultiPolygon
import shapely
from shapely.ops import unary_union
import logging
import gpxpy.gpx
from lxml import etree
from pydantic import BaseModel
from osm_merge.backend.egress_models import DBsIn, Response

class Item(BaseModel):
    name: str = "foo"
    description: str | None = None

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="Egress Planning",
    version="0.1",
    )

# outer = APIRouter(
#     prefix="/helper",
#     tags=["helper"],
#     responses={404: {"description": "Not found"}},
# )

class Egress(RouteAddrs):
    def __init__(self):
        """
        """
        self.aoi = None
        self.major = None
        self.gpx = None
        super().__init__()
        self.connectDB("colorado", "gilpin_routing")
        self.create_highway_view("/tmp/Gilpin.geojson")
        self.create_address_view("/tmp/Gilpin.geojson")
        self.calculate_aoi()

    def calculate_aoi(self) -> MultiPolygon:
        """
        """
        polys = list()
        major = self._get_highways()
        for name, values in major.items():
            polys.append(values["buffer"])
            self.get_vertics(name)
            self.aoi = unary_union(polys)
        return self.aoi

    def make_db_views(self,
                     filespec: str,
                        ):
        """
        """
        self.create_highway_view(filespec)
        self.create_address_view(filespec)

    def _get_highways(self):
        """
        """
        self.major = self.find_major_highways()
        return self.major
        
    def process_routes (self,
                        routes: list,
                        start: Point,
                        targets: list,
                        ) -> str:
        """
        """
        tracks = list()
        gpx = gpxpy.gpx.GPX()
        gpx.nsmap = {'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3'}
        gpx.creator = "egress 0.1"
        
        for route in routes:
            gpx_track = gpxpy.gpx.GPXTrack()
            # gpx_track.name = f"{addr["number"]} {addr["street"]} Track #{routes.index(route)}"
            gpx.tracks.append(gpx_track)
            cnt = len(route) - 1
            # print(f"ROUTE: {route[0]["node"]}, {route[0]["edge"]} : {route[cnt]["node"]}, {route[cnt]["edge"]}")
            part, done = self.make_track(route, targets)
            gpx_track.segments.append(part)
            # Make the first point in the track be the address node so it's clear
            # which house uses which route.
            gpx.tracks[0].segments[0].points.insert(0, gpxpy.gpx.GPXTrackPoint(start.y, start.x))
            #  outfile = f"{addr["number"]}_{addr["street"].replace(" ", "_")}.gpx"
            dist = etree.Element("{gpxx}length", nsmap=gpx.nsmap)
            dist.text = f"Length {gpx_track.length_2d():.3f} meters or {(gpx_track.length_2d() / 0.3048):.3f} feet"
            gpx_track.extensions.append(dist)
        self.gpx = gpx
        return gpx.to_xml()

#
# These are the public APIs
#
egress = Egress()
    
@app.get("/")
# FIXME: the default database names are only for debugging!
async def get_default (osmdb: Annotated[str, Query()] = "colorado",
                       routedb: Annotated[str, Query()] = "gilpin_routing"):
    if osmdb is None and routedb is None:
        # FIXME: these are just for debugging"
        result = egress.connectDB(osmdb, routedb)
    return f"uri: {osmdb}, routedb: {routedb}"

@app.post("/aoi")
async def apply_aoi(file: UploadFile = File(...)):
    egress.create_highway_view(file.filename)
    egress.create_address_view(file.filename)
    return {
        "filename": file.filename,
        "content_type": file.content_type,
    }

# FIXME: Drop the default values after debugging!
@app.get("/address")
async def get_route_for_address (number: Annotated[str, Query()] = "1305",
                                 street: Annotated[str, Query()] = "Upper Moon Gulch Road"):
    addr = egress.get_geom(number, street)
    node = shapely.wkt.loads(addr["geom"])[0]
    log.debug(f"Address {number} {street} is {node}")
    return get_route_for_coordinates (node.x, node.y)

# FIXME: Drop the default values after debugging!
@app.get("/coordinates")
async def get_route_for_coordinates (lat: float = -105.51833,
                                     lon: float = 39.91271) -> dict:
    """
    Args:
        lat (float): the latitude
        lon (float): the longitude
    """
    breakpoint()
    node = Point(lat, lon)
    if node is None:
        log.warning(f"No suitable highways were found near {node}")
        return {"ERROR": "No suitable highways were found near {node}"}

    nearest = egress.find_nearest_vertex(node)
    if len(nearest) == 0:
        log.warning(f"No suitable nodes were found near {node}")
        return {"error": f"No suitable nodes were found near {node}"}
    else:
        log.debug(f"Found nearest vertex {nearest} to {node}")
    pt = shape(nearest["geom"])
    targets = egress.get_targets(pt, egress.aoi)

    if len(targets) == 0:
        log.warning(f"No targets found for {pt}")
        return {"ERROR": f"No targets found for {pt}"}
    else:
        log.debug(f"Found targets {targets}")
        routes = egress.make_route(nearest["id"], targets)
        if len(routes) == 0:
            log.warning(f"No routes were found!")
            return {"ERROR": "No routes were found!"}
        else:
            log.debug(f"There are {len(routes)} routes in the result.")
            gpx = egress.process_routes(routes, node, targets)

    return {"nearest": nearest, "targets": targets, "gpx": gpx}

@app.get("/download")
async def download_gpx (outfile: str) -> bool:
    with open(outfile, "w") as gpxfile:
        if egress.gpx is None:
            log.error(f"No GPX data!")
            return False
        else:
            gpxfile.write(egress.gpx.to_xml())
            log.debug(f"Wrote {outfile}")
    # return f"apply_aoi({file.filename})"
    return True

