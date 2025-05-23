#!/usr/bin/python3

# Copyright (c) 2025 OpenStreetMap US
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

import argparse
import logging
import re
import sys
import os

# import lxml
from lxml import etree
import xml.etree.ElementTree as treepair

from osm_merge.yamlfile import YamlFile

import osm_merge as om
rootdir = om.__path__[0]

# Instantiate logger
log = logging.getLogger(__name__)

class Yaml2XForm(object):
    def __init__(self,
                 yamlspec: str = None,
                 ):
        """
        This class processes the YAML file for an XForm

        Args:
            yamlspec (str): The YAML config file for converting data

        Returns:
            (Yaml2XForm): An instance of this class
        """
        if yamlspec is not None:
            if yamlspec[:2] != "./":
                filespec = f"{rootdir}/{yamlspec}"
            else:
                filespec = yamlspec
            if not os.path.exists(filespec):
                log.error(f"{yamlspec} does not exist!")
                quit()

            yaml = YamlFile(filespec)
            self.config = yaml.getEntries()
        else:
            logging.error("Need to specify a config file!")
        # yaml.dump()

        self.defaults = dict()
        xmln = {
            "xmlns": "http://www.w3.org/2002/xforms",
            "xmlns:h": "http://www.w3.org/1999/xhtml",
            "xmlns:ev": "http://www.w3.org/2001/xml-events",
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:jr": "http://openrosa.org/javarosa",
            "xmlns:orx": "http://openrosa.org/xforms",
            "xmlns:odk": "http://www.opendatakit.org/xforms",
        }

        self.parse_config()

        # Register the namespaces
        self.root = etree.Element('xml', version="1.0")
        head = etree.Element('head')
        body = etree.Element('body')
        self.root.append(head)
        self.root.append(body)
        for key, value in xmln.items():
            if key.find(':') > 0:
                colon = key.split(':')
                etree.register_namespace(colon[1], value)
            else:
                etree.register_namespace(key, value)


        title = etree.Element("title")
        title.text = "Hello World!"
        head.append(title)
        model = etree.Element("model")
        model.set("xforms-version", "")
        head.append(model)
        itext = etree.Element("itext")
        lang = etree.Element("translation", lang="")
        itext.append(lang)
        model.append(itext)

        self.get_choices(lang)
        self.get_questions(lang)
        self.add_geopoint(lang)
        self.add_instance(model)
        self.add_choices(itext)
        self.add_nodeset(itext)
        print(etree.tostring(self.root, pretty_print=True).decode())

    def lookup_value(self,
                     value: str,
                     ) -> str:
        """
        """
        for group in self.config["survey"]["groups"]:
            for entry in group:
                for item in group[entry]:
                    [[k, v]] = item.items()
                    return f"/data/{entry}/{v}"

    def add_nodeset(self,
                      element: etree.Element,
                      ):
        """
        Create the bind section
        """
        # bind attributes are:
        # nodeset, type, readonly, required, relevant, constraint, calculate,
        # saveIncomplete, jr:requiredMsg, jr:constraintMsg, jr:preload,
        # jr:preloadParams
        #
        # Data Types are string, int, boolean, decimal, date, time, dateTime
        # geopoint, geotrace, geoshape, binary, barcode, intent

        # These are the header block, internal ODK Coll\lect variables
        # so we have information about each chunk of data that is collected.
        for item in self.config["survey"]["header"]:
            [[k, v]] = item.items()
            if v == "dateTime":
                bind = etree.Element("bind",
                                     nodeset=f"/data/{k}",
                                     jr_preload="timestamp",
                                     type=v,
                                     jr_preloadParams=k)
                element.append(bind)
            elif v == "geopoint":
                # bind = etree.Element("bind", odk_setpoint="", ref="", event="")
                bind = etree.Element("bind", nodeset=f"/data/{k}", type="geopoint")
                element.append(bind)
                pass
            elif v == "int":
                pass
            elif v == "boolean":
                pass
            elif v == "string":
                bind = etree.Element("bind", nodeset=f"/data/{k}",
                                     jr_preload="property",
                                     type="string",
                                     jr_preloadParams=k)
                element.append(bind)

        # These are the questions to ask
        # default, required, parameters, apperance
        defaults = {"nodeset": "",
                    # "jr_preload": "",
                    "type": "",
                    # "jr_preloadParams": ""
                }

        # Get the list of groups
        # punc = ("=", "!=", "<", ">")
        punc = ("=")
        for item in self.config["survey"]["groups"]:
            [[k, v]] = item.items()
            for entry in v:
                [[k2, v2]] = entry.items()
                if k2[:7] != "select_":
                    continue
                defaults["nodeset"] = f"/data/{k}/{v2}"
                for attribute in self.config["questions"][v2]:
                    [[k3, v3]] = attribute.items()
                    print(f"FIXME: {k3} = {v3}")
                    if k3 == "required" or k3 == "readonly":
                        defaults[k2] = "true()"
                    if k3 == "relevant":
                        value = str()
                        if v3.find(" or ") > 0:
                            for i in v3.split(" or "):
                                for test in punc:
                                    if i.find(test) > 0:
                                        tmp = i.split(test)
                                        xpath = self.lookup_value(i.split(tmp[0]))
                                        value += f"{xpath} {test}'{tmp[1]}' or "
                                        break
                        if v3.find(" and ") > 0:
                            for i in v3.split(" and "):
                                for test in punc:
                                    if i.find(test) > 0:
                                        tmp = i.split(test)
                                        xpath = self.lookup_value(i.split(tmp[0]))
                                        value += f"{xpath} {test}'{tmp[1]}' and )"
                                        break
                        # Drop the trailing conditional
                        if value[-1:] == " ":
                            pos = value[:-1].rfind(" ")
                        defaults[k3] = value[:pos]

            bind = etree.Element("bind")
            for key, value in defaults.items():
                bind.set(key, value)
            element.append(bind)

        # for key, value in self.config["questions"].items():
        #     # These are the deself.config["questions"][v2]faults
        #     if key == "required" or key == "readonly":
        #         defaults[key] = "true()"
        #     elif key == "geopoint":
        #         bind = etree.Element("odk_setgeopoint", ref="", event="")
        #         continue
        #     elif key == "image":
        #         bind = etree.Element("bind", nodeset="", type="", orx_max_pixels="")
        #         continue
        #     if key == "relevant":
        #         # FIXME: this needs xpath support
        #         defaults[k] = ""

        #     bind = etree.Element("bind",
        #                          nodeset="",
        #                          jr_preload="",
        #                          type="",
        #                          jr_preloadParams="")
        #     element.append(bind)

    def add_choices(self,
                      element: etree.Element,
                      ):
        for key, value in self.config["choices"].items():
            index = 0
            root = etree.Element(self.root.tag)
            instance = etree.Element("instance", id="")
            for entry in value: 
                item = etree.Element("item")
                [[k2, v2]] = entry.items()
                itextid = etree.Element("itextId")
                itextid.text = f"{key}-{index}"
                item.append(itextid)
                name = etree.Element("name")
                name.text = k2
                item.append(name)
                index += 1
                root.append(item)
            instance.append(root)
            element.append(instance)

    def add_geopoint(self,
                      element: etree.Element,
                      ):
        """
        Make the GeoPoint entry.
        """
        element.append(self.make_text("Record the location where you are standing"))
        for blank in range(0, 26):
            element.append(self.make_text("-"))

    def add_instance(self,
                      element: etree.Element,
                      ):
        """
        Create an instance and add it to the element tree.
        """
        instance = etree.Element("instance")
        data = etree.Element("data", id="", version="")
        data.append(etree.Element("start"))
        data.append(etree.Element("end"))
        data.append(etree.Element("today"))
        data.append(etree.Element("deviceid"))
        data.append(etree.Element("phonenumber"))
        data.append(etree.Element("username"))
        data.append(etree.Element("email"))
        data.append(etree.Element("warmup"))

        # ignore = ("geopoint", "geotrace", "image", "text", "select_one", "select_multiple")
        ignore = ("geopoint", "geotrace", "image", "text")
        for entry in self.config["survey"]["groups"]:
            for key, value in entry.items():
                screen = etree.Element(key)
                data.append(screen)
                if type(value) == list:
                    for item in value:
                        [[k, v]] = item.items()
                        if k in ignore:
                            continue
                        if k == "text":
                            element.append(self.make_text(v))
                            continue
                        v2 = etree.Element(v)
                        if v in self.defaults:
                            v2.text = self.defaults[v]

                        screen.append(v2)

        meta = etree.Element("meta")
        meta.append(etree.Element("instanceID"))
        data.append(meta)
        instance.append(data)
        element.append(instance)   
        
    def get_choices(self,
                    element: etree.Element,
                    ):
        for key, value in self.config["choices"].items():
            if type(value) == list:
                for label in value:
                    if type(label) == str:
                        element.append(self.make_text(label))
                    else:
                        [[k, v]] = label.items()
                        element.append(self.make_text(v))

    def get_questions(self,
                    element: etree.Element,
                    ):
        """
        Get all the questions from the config file.
        """
        for key, value in self.config["questions"].items():
            if type(value) == list:
                for label in value:
                    [[k, v]] = label.items()
                    if k == "question":
                        element.append(self.make_text(v))
                    elif k == "default":
                        self.defaults[key] = v

    def make_text(self,
                  entry = str(),
                  ) -> etree.Element:
        """
        Get all the choices from the config file.
        """
        text = etree.Element("text", id="")
        value = etree.Element("value")
        value.text = entry
        text.append(value)
        return text

    def parse_config(self):
        """
        Parse the YAML config file.
        """
        for item in self.config["survey"]["groups"]:
            [[k, v]] = item.items()
            if type(v) == list:
                for entry in v:
                    if type(entry) == dict:
                        [[k2, v2]] = entry.items()
                        select_one = list()
                        if k2 == "select_one":
                            select_one = v2
                        elif k2 == "select_multiple":
                            # self.select_multiple(v2)
                            pass
                        print(f"FIXME: {k2}, {v2}")
                    else:
                        print(f"FIXME2: {k} {v}")
                        

#
# This script can be run standalone for debugging purposes. It's easier to debug
# this way than using pytest,
#
def main():
    """This main function lets this class be run standalone by a bash script."""
    parser = argparse.ArgumentParser(description="Read and parse a YAML file")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-y", "--yaml", required=True, default="xform.yaml",
                        help="Default Yaml file")
    args = parser.parse_args()

    # if verbose, dump to the terminal.
    if args.verbose is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format=("%(threadName)10s - %(name)s - %(levelname)s - %(message)s"),
            datefmt="%y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )

    config = Yaml2XForm(args.yaml)
    
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
