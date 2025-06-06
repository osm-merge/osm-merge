//
// Copyright (c) 2024, 2025 OpenStreetMap US
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// GPLv3! The osmium command tools are great, but I wanted
// something that could clip data and filter it focused on highways.

// This is generated by autoconf
#ifdef HAVE_CONFIG_H
#include "osmconfig.h"
#endif

// #include <sstream>
#include <filesystem>
#include <unistd.h>
#include <stdio.h>
#include <csignal>

namespace fs = std::filesystem;

#include "fastclip.hh"
#include "tqdm.h"

class MyHandler : public osmium::handler::Handler {
private:
    std::shared_ptr<multipolygon_t> aoi;
    osmium::geom::WKTFactory<> factory;
    static constexpr const std::size_t buffer_size = 10UL * 1024UL * 1024UL;
    osmium::memory::Buffer m_buffer{buffer_size,
        osmium::memory::Buffer::auto_grow::no};
    std::unique_ptr<osmium::io::Writer> m_writer;

public:
    void add_aoi(const std::string &filespec) {
        BOOST_LOG_TRIVIAL(debug) << "Adding a Area Of Interest for the data extract";
        auto fastclip = FastClip();
        auto boundary = fastclip.readAOI(filespec);
        aoi = fastclip.make_geometry(boundary.as_object());
        // BOOST_LOG_TRIVIAL(debug) << boost::geometry::wkt(*aoi);
    }
    // The callback functions can be either static or not depending on whether
    // you need to access any member variables of the handler.
    void way(const osmium::Way& way) {
        std::string highway = factory.create_linestring(way);
        // BOOST_LOG_TRIVIAL(debug) << "way " << way.id();
        linestring_t line;
        boost::geometry::read_wkt(highway, line);
        if (boost::geometry::intersects(line, *aoi) || boost::geometry::within(line, *aoi)) {
            BOOST_LOG_TRIVIAL(debug) << "Way " << way.id() << " is within the AOI";
        } else {
            BOOST_LOG_TRIVIAL(debug) << "Way " << way.id() << " is not within the AOI";
        }
# if 0
        for (const auto& nr : way.nodes()) {
            double lon = nr.location().lon();
            double lat = nr.location().lat();
            point_t point(lon, lat);
            // BOOST_LOG_TRIVIAL(debug) << "  osm node " << nr.ref() << " " << boost::geometry::wkt(point) << " : " << nr.location();
            // BOOST_LOG_TRIVIAL(debugmv tr) << "  node " << nr.ref() << " " << nr.location();
            // for (auto it = aoi->begin(); it!= aoi->end(); ++it) {
            if (boost::geometry::within(point, *aoi)) {
                BOOST_LOG_TRIVIAL(debug) << "Node " << nr.ref() << " is within the AOI";
            } else {
                BOOST_LOG_TRIVIAL(debug) << "Node " << nr.ref() << " is not within the AOI";
            }
        }
#endif
    }
    void dump() {
        if (boost::geometry::is_empty(*aoi)) {
            std::cerr << "AOI is empty!" << std::endl;
        } else  {
            std::cerr << "AOI contains " << boost::geometry::num_geometries(*aoi) << " geometries" << std::endl;
        }
    }
};

bool
FastClip::create_node_cache(const std::string &infile,
                            const std::string &cachefile) {
    osmium::io::Reader reader{infile, osmium::osm_entity_bits::node};
    osmium::ProgressBar progress_bar{reader.file_size(), osmium::isatty(2)};

    const int fd = ::open(cachefile.c_str(), O_RDWR | O_CREAT | O_TRUNC, 0666);
    if (fd == -1) {
        BOOST_LOG_TRIVIAL(error) << "Can not open location cache file '" << cachefile << "': " << std::strerror(errno);
        return 1;
    }
    BOOST_LOG_TRIVIAL(info) << "Creating node cache, which may take awhile...";
    index_type index{fd};
    location_handler_type location_handler{index};
    osmium::apply(reader, location_handler);
    reader.close();
    progress_bar.done();

    return true;
}

std::string
FastClip::check_index_type(const std::string& index_type_name) {
    std::string type{index_type_name};
    const auto pos = type.find(',');
    if (pos != std::string::npos) {
        type.resize(pos);
    }

    return index_type_name;
}

void
FastClip::add_filter(osmium::osm_entity_bits::type entities,
                     const osmium::TagMatcher& matcher) {
    if (entities & osmium::osm_entity_bits::node) {
        m_filters(osmium::item_type::node).add_rule(true, matcher);
    }
    if (entities & osmium::osm_entity_bits::way) {
        m_filters(osmium::item_type::way).add_rule(true, matcher);
    }
    if (entities & osmium::osm_entity_bits::relation) {
        m_filters(osmium::item_type::relation).add_rule(true, matcher);
    }
}

void
FastClip::add_nodes(const osmium::Way& way) {
    for (const auto& nr : way.nodes()) {
        m_ids(osmium::item_type::node).set(nr.positive_ref());
    }
}

void
FastClip::copy_data(osmium::ProgressBar& progress_bar,
                    osmium::io::Reader& reader,
                    osmium::io::Writer& writer,
                    location_handler_type& location_handler) {
    while (osmium::memory::Buffer buffer = reader.read()) {
        progress_bar.update(reader.offset());
        osmium::apply(buffer, location_handler);

        if (true) {
            writer(std::move(buffer));
        } else {
            for (const auto& object : buffer) {
                if (object.type() != osmium::item_type::node || !static_cast<const osmium::Node&>(object).tags().empty()) {
                    writer(object);
                }
            }
        }
    }
}

std::shared_ptr<multipolygon_t>
FastClip::make_geometry(const std::string &wkt) {
    // Convert a WKT string into a geometry
    auto geom = boost::geometry::from_wkt<multipolygon_t>(wkt);
    auto mpoly = std::make_shared<multipolygon_t>(geom);

    return mpoly;
}

std::shared_ptr<multipolygon_t>
FastClip::make_geometry(const json::value &val) {
    auto mpoly = std::make_shared<multipolygon_t>();
    if (val.is_array()) {
        auto &array = val.get_array();
        //tqdm bar;
        //init_tqdm(&bar, "Processing", false, "tasks", true, array.size(), 5);
        std::vector<point_t> points;
        polygon_t poly;
        for (auto it = array.begin(); it!= array.end(); ++it) {
            //update_tqdm(&bar, 1, true);
            if (it->is_array()) {
                if (it->at(0).is_array()) {
                    auto array2 = it->at(0).get_array();
                    auto foo = make_geometry(array2);
                    // BOOST_LOG_TRIVIAL(debug) << "YES: " << boost::geometry::wkt(*foo);
                    for (auto iit = foo->begin(); iit!= foo->end(); ++iit) {
                        // BOOST_LOG_TRIVIAL(debug) << "NO WAY: " << boost::geometry::wkt(*iit);
                        for (auto iitt = foo->begin(); iitt!= foo->end(); ++iitt) {
                            mpoly->push_back(*iitt);
                            for (auto iittt = foo->begin(); iittt!= foo->end(); ++iittt) {
                                // BOOST_LOG_TRIVIAL(debug) << "NO WAY 2: " << boost::geometry::wkt(*iittt);;
                                mpoly->push_back(*iittt);
                            }
                        }
                    }
                    continue;
                } else {
                    double lat = it->at(0).as_double();
                    double lon = it->at(1).as_double();
                    point_t point(lat, lon);
                    // BOOST_LOG_TRIVIAL(debug) << "NO: " << boost::geometry::wkt(point);
                    points.push_back(point);
                }
            }
        }
        boost::geometry::assign_points(poly, points);
        // for (auto iit = poly.begin(); iit!= poly.end(); ++iit) {
        // BOOST_LOG_TRIVIAL(debug) << "FOO: " << boost::geometry::num_geometries(poly);
        // }
        mpoly->push_back(poly);
        //close_tqdm(&bar);
    } else {
        BOOST_LOG_TRIVIAL(error) << "Is not an array()";
    }

    return mpoly;
}

std::shared_ptr<multipolygon_t>
FastClip::make_geometry(const json::object &obj) {
    auto mpoly = std::make_shared<multipolygon_t>();
    if (obj.empty()) {
      BOOST_LOG_TRIVIAL(error) << "Object has no entries!";
      return mpoly;
    }
    BOOST_LOG_TRIVIAL(debug) << "Object has " << obj.size() << " entries" << std::endl;
    auto data = json::parse(json::serialize(obj));
    auto foo = data.at("features");
    auto features = foo.get_array();
    for (auto it = features.begin(); it!= features.end(); ++it) {
      auto &geom = it->at("geometry");
      auto &props = it->at("properties");
      auto &coords = geom.at("coordinates");//
      auto polys = make_geometry(coords);
      for (auto iit = polys->begin(); iit!= polys->end(); ++iit) {
          mpoly->push_back(*iit);
      }
      // mpoly->push_back(*polys);
    }

    return mpoly;
}

bool
FastClip::filterFile(const std::string &infile,
                    const std::string &outfile) {
    // Filter anything not a highway.
    std::filesystem::path datafile = infile;
    if (!std::filesystem::exists(datafile)) {
        BOOST_LOG_TRIVIAL(error) << "Data file not found: " << datafile;
        return false;
    }

    // std::string informat = std::filesystem::path(infile).extension();
    // std::string outformat = std::filesystem::path(outfile).extension();
    const osmium::io::File input_file{infile};
    const osmium::io::File output_file{outfile};

    // tell it to only read ways.
    osmium::io::Reader reader{infile, osmium::osm_entity_bits::way};
    osmium::io::Header header = reader.header();
    header.set("generator", "fastclip");

    // Create the node cache if it doesn't exist.
    if (!std::filesystem::exists("node_cache")) {
      create_node_cache(infile, "node_cache");
    }
    // Initialize location index on disk using an existing file.
    const int fd = ::open("node_cache", O_RDWR);
    if (fd == -1) {
        BOOST_LOG_TRIVIAL(error) << "Can not open location cache file" << std::strerror(errno);
        return 1;
    }
    index_type index{fd};
    // The handler that adds node locations from the index to the ways.
    location_handler_type location_handler{index};
    // Feed all ways through the location handler and then our own handler.
    MyHandler handler;
    handler.add_aoi("/play/MapData/Boundaries/US-States/Utah.geojson");
    osmium::io::Writer writer{outfile, header, osmium::io::overwrite::allow};

    osmium::TagsFilter hfilter{false};
    hfilter.add_rule(true, "highway", "path");
    hfilter.add_rule(true, "highway", "footway");
    hfilter.add_rule(true, "highway", "track");
    hfilter.add_rule(true, "highway", "unclassified");
    hfilter.add_rule(true, "highway", "residential");
    hfilter.add_rule(true, "highway", "tertiary");
    hfilter.add_rule(true, "highway", "primary");
    hfilter.add_rule(true, "highway", "secondary");

    // Get all ways matching the highway filter
    osmium::ProgressBar progress_bar{reader.file_size(), osmium::isatty(2)};
    try {
        while (osmium::memory::Buffer buffer = reader.read()) {
            // BOOST_LOG_TRIVIAL(debug) << reader.offset();
            progress_bar.update(reader.offset());
            for (const auto& way : buffer.select<osmium::Way>()) {
                if (osmium::tags::match_any_of(way.tags(), hfilter)) {
                    // Cache the node refs
                    add_nodes(way);
                    writer(way);
                }
            }
            if (reader.eof()) {
                break;
            }
        }
    } catch (const osmium::io_error& e) {
        // All exceptions used by the Osmium library derive from std::exception.
        BOOST_LOG_TRIVIAL(error) << infile << ": " << e.what();
        return 1;
    }

    progress_bar.done();
    writer.close();
    // reader.close();
    BOOST_LOG_TRIVIAL(info) << "Wrote " << outfile;
#if 0
    BOOST_LOG_TRIVIAL(debug) << "Copying input file '" << infile << "'\n";
    osmium::io::Reader reader2{infile, osmium::osm_entity_bits::way};
    osmium::io::Header header2 = reader2.header();
    osmium::io::Writer writer2{"out2.pbf", header, osmium::io::overwrite::allow};
    header2.set("generator", "fastclip");
    // osmium::io::Reader reader{infile};
    // osmium::io::Header header{reader.header()};
    // setup_header(header);
    osmium::ProgressBar progress_bar2{reader2.file_size(), osmium::isatty(2)};
    copy_data(progress_bar2, reader2, writer2, location_handler);
    progress_bar2.done();

#endif

    // writer.close();
    // reader.close();
    BOOST_LOG_TRIVIAL(info) << "Wrote " << outfile;
    return true;
}

// CPLSetConfigOption( "OGR_GEOJSON_MAX_OBJ_SIZE", "0" );
json::value
FastClip::readAOI(const std::string &filespec) {
    json::stream_parser p;
    boost::system::error_code ec;
    auto f = std::fopen(filespec.c_str(), "r");
    do {
        char buf[4096];
        auto const nread = std::fread( buf, 1, sizeof(buf), f );
        p.write( buf, nread, ec );
    }
    while( ! feof(f) );
    std::fclose(f);

    auto result = p.release();
    aoi = make_geometry(result.as_object());

    return result;
}

// Local Variables:
// mode: C++
// indent-tabs-mode: nil
// End:
