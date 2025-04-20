//
// Copyright (c) 2024, 2025 OpenStreetMap US
//
// This file is part of Underpass.
//
//     This is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     Underpass is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with Underpass.  If not, see <https://www.gnu.org/licenses/>.
//

#ifndef __FASTCLIP_HH_
#define __FASTCLIP_HH_

#include <boost/geometry.hpp>
#include <boost/log/trivial.hpp>
#include <boost/json.hpp>
using namespace boost;
namespace logging = boost::log;
namespace json = boost::json;

typedef boost::geometry::model::d2::point_xy<double> point_t;
typedef boost::geometry::model::polygon<point_t> polygon_t;
typedef boost::geometry::model::multi_polygon<polygon_t> multipolygon_t;
typedef boost::geometry::model::linestring<point_t> linestring_t;
typedef boost::geometry::model::multi_linestring<linestring_t> multilinestring_t;

#include <osmium/geom/ogr.hpp>
#include <osmium/tags/filter.hpp>
#include <osmium/tags/tags_filter.hpp>
#include <osmium/util/progress_bar.hpp>
#include <osmium/tags/matcher.hpp>
#include <osmium/io/any_input.hpp>
#include <osmium/io/any_output.hpp>
#include <osmium/index/id_set.hpp>
#include <osmium/index/nwr_array.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/index/map/dense_file_array.hpp>
#include <osmium/geom/ogr.hpp>
#include <osmium/area/multipolygon_manager.hpp>
#include <osmium/io/any_output.hpp>
#include <osmium/index/nwr_array.hpp>
#include <osmium/index/id_set.hpp>

using index_type = osmium::index::map::DenseFileArray<osmium::unsigned_object_id_type, osmium::Location>;
using location_handler_type = osmium::handler::NodeLocationsForWays<index_type>;

class FastClip {
private:
    // FIXME: these should really be shared pointers
    // Only keep the outer polygons.
    std::map<std::string, const OGRGeometry *> outers;
    // std::shared_ptr<const OGRGeometry> boundaries;
    OGRMultiPolygon boundaries;
    osmium::nwr_array<osmium::TagsFilter> m_filters;
    osmium::nwr_array<osmium::index::IdSetDense<osmium::unsigned_object_id_type>> m_ids;
    // bool m_invert_match = false;
    osmium::index::IdSetSmall<osmium::unsigned_object_id_type> m_member_node_ids;
    void copy_data(osmium::ProgressBar& progress_bar,
                   osmium::io::Reader& reader,
                   osmium::io::Writer& writer,
                   location_handler_type& location_handler);
    std::string check_index_type(const std::string& index_type_name);
    // bool writeOuters(const std::string &filespec);
    bool display_progress() const;
public:
    void add_filter(osmium::osm_entity_bits::type entities,
                    const osmium::TagMatcher& matcher);
    void add_nodes(const osmium::Way& way);
    std::shared_ptr<multipolygon_t> make_geometry(const std::string &wkt);
    std::shared_ptr<multipolygon_t> make_geometry(const json::object &obj);
    std::shared_ptr<multipolygon_t> make_geometry(const json::value &val);
    bool filterFile(const std::string &infile,
                    const std::string &outfile);
    json::value readAOI(const std::string &filespec);
};

#endif

// Local Variables:
// mode: C++
// indent-tabs-mode: nil

// End:
