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
from lxml import etree
import yaml

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
        else:
            logging.error("Need to specify a config file!")
        # yaml.dump()

        self.defaults = dict()
        self.xmln = {
            # "xmlns": "http://www.w3.org/2002/xforms",
            "h": "http://www.w3.org/1999/xhtml",
            "ev": "http://www.w3.org/2001/xml-events",
            "xsd": "http://www.w3.org/2001/XMLSchema",
            "jr": "http://openrosa.org/javarosa",
            "orx": "http://openrosa.org/xforms",
            "odk": "http://www.opendatakit.org/xforms",
        }

        # self.parse_config()

        filespec = yamlspec
        if not os.path.exists(filespec):
            log.error(f"{yamlspec} does not exist!")
            quit()

        self.data = dict()
        self.file = open(filespec, "rb").read()
        self.yaml = yaml.load(self.file, Loader=yaml.Loader)
        self.config = self.getEntries()

        # Register the namespaces
        self.root = etree.Element('xml', version="1.0", nsmap=self.xmln)
        # self.root = etree.Element('xml', version="1.0")
        head = etree.Element('h_head')
        body = etree.Element('h_body')
        self.root.append(head)
        self.root.append(body)
        title = etree.Element("h_title")
        title.text = self.config["settings"]["form_title"]
        head.append(title)
        model = etree.Element("model")
        model.set("odk_xforms-version", "1.0.0")
        head.append(model)
        itext = etree.Element("itext")
        lang = etree.Element("translation", lang="")
        itext.append(lang)
        model.append(itext)

        # first is all the labels of the choices
        self.get_choices(lang)
        # then they get a blank default as a placeholer
        self.set_choices(lang)
        # Then the instances
        self.add_instance(model)
        self.add_geopoint(lang)
        self.add_choices(itext)
        self.get_questions(lang)
        self.add_nodeset(itext)

        self.add_appearance(body)
        file = open("out.xml", "w")
        out = etree.tostring(self.root, pretty_print=True).decode()
        # print(etree.tostring(self.root, pretty_print=True).decode())
        # FIXME: python doesn't allow you to use the colon character,
        # which was screwing up the attributes with a namespace. So
        # we fix the output string as it's simple.
        out = etree.tostring(self.root, pretty_print=True).decode()
        file.write(out.replace("jr_", "jr:").replace("odk_", "odk:").replace("orx_", "orx:").replace("h_", "h:"))

    def getEntries(self):
        """
        Convert the list from the YAML file into a searchable data structure

        Returns:
            (dict): The parsed config file
        """
        columns = list()
        for entry in self.yaml:
            for key, values in entry.items():
                self.data[key] = dict()
                # values is a list of dicts which are tag/value pairs
                for item in values:
                    # print(f"YAML: {item}")
                    [[k, v]] = item.items()
                    if type(v) == str:
                        self.data[key][k] = v
                    elif type(v) == float or type(v) == int:
                        self.data[key][k] = str(v)
                    elif type(v) == list:
                        self.data[key][k] = dict()
                        for newval in v:
                            if newval is None:
                                continue
                            [[k2, v2]] = newval.items()
                            self.data[key][k][k2] = dict()
                            if type(v2) == list:
                                for subval in v2:
                                    [[k3, v3]] = subval.items()
                                    if k3[:7] != "select_":
                                        self.data[key][k][k2][k3] = v3
                                    else:
                                        breakpoint()
                                        for val in v3:
                                            self.data[key][k][k2][k3]
                                            pass
                                    # self.data[] = ""
                                    # breakpoint()
                            else:
                                self.data[key][k].update(newval)
                    else:
                        log.error(f"{type(v)} is not suported.")

        # breakpoint()
        return self.data

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

    def add_appearance(self,
                       element: etree.Element,
                      ):
        """
        """
        for k, v in self.config["survey"]["groups"].items():
            if "appearance" in v:
                appear = etree.Element("group",
                                   appearance=v["appearance"],
                                   ref=f"/data/{k}")
                label = etree.Element("label",
                                      ref=f"jr_itext('/data/{k}:label')")
                appear.append(label)
                element.append(appear)

            for k2, v2 in v.items():
                tmp = dict()
                if type(v2) == str:
                    tmp[k2] = v2
                    continue
                for k3 in v2:
                    [[k4, v4]] = k3.items()
                    tmp[k4] = v4
                print(f"TMP: {tmp}")
                if tmp["type"][:7] == "select_":
                    select = etree.Element("select1",
                                           appearance=tmp["appearance"],
                                           ref=f"/data/{k}/{tmp["name"]}")
                    label = etree.Element("label",
                                          ref=f"jr_itext('/data/{k}/{tmp["name"]}:label')")
                    select.append(label)
                    for x in self.config["choices"][k2]:
                        item = etree.Element("item")
                        choice = etree.Element("label")
                        choice.text = ""
                        value = etree.Element("value")
                        value.text = x
                        item.append(choice)
                        item.append(value)
                        select.append(item)
                    appear.append(select)
                    element.append(appear)
                for k2, v2 in v.items():
                    select = etree.Element("select1", ref=f"jr_itext('/data/{k2}:label')")
            else:
                pass

    def add_nodeset(self,
                      element: etree.Element,
                      ):
        """
        Create the bind section.
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
        for key, value in self.config["survey"]["header"].items():
            if value == "dateTime":
                bind = etree.Element("bind",
                                     nodeset=f"/data/{key}",
                                     jr_preload="timestamp",
                                     type=value,
                                     jr_preloadParams=key,
                                     )
                element.append(bind)
            elif value == "geopoint":
                bind = etree.Element("bind", nodeset=f"/data/{key}", type="geopoint")
                element.append(bind)
            elif value == "int":
                pass
            elif value == "boolean":
                pass
            elif value == "string":
                bind = etree.Element("bind", nodeset=f"/data/{key}",
                                     jr_preload="property",
                                     type="string",
                                     jr_preloadParams=key)
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
        for k, v in self.config["survey"]["groups"].items():
            for k2, v2 in v.items():
                if k2[:7] != "select_":
                    continue
                defaults["nodeset"] = f"/data/{k}/{v2}"
                for attribute in self.config["questions"][v2]:
                    if not attribute:
                        continue
                    [[k3, v3]] = attribute.items()
                    # print(f"FIXME: {k3} = {v3}")
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
            for entry, val in value.items():
                item = etree.Element("item")
                itextid = etree.Element("itextId")
                itextid.text = f"{key}-{index}"
                item.append(itextid)
                name = etree.Element("name")
                name.text = val
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
        # element.append(self.make_text("Record the location where you are standing"))
        # for blank in range(0, 26):
        #    element.append(self.make_text("-"))
        pass

    def add_instance(self,
                      element: etree.Element,
                      ):
        """
        Create an instance and add it to the element tree.
        """
        # These are all internal to ODK Collect
        id =  self.config["settings"]["form_id"]
        version =  self.config["settings"]["version"]
        data = etree.Element("data", id=id, version=version)
        data.append(etree.Element("start"))
        data.append(etree.Element("end"))
        data.append(etree.Element("today"))
        data.append(etree.Element("deviceid"))
        data.append(etree.Element("phonenumber"))
        data.append(etree.Element("username"))
        data.append(etree.Element("email"))
        data.append(etree.Element("warmup"))

        instance = etree.Element("instance", id="")
        # ignore = ("geopoint", "geotrace", "image", "text", "select_one", "select_multiple")
        ignore = ("geopoint", "geotrace", "image", "text")
        for group, values in self.config["survey"]["groups"].items():
            for key, value in values.items():
                screen = etree.Element(key)
                data.append(screen)
                if type(value) == list:
                    for item in value:
                        [[k, v]] = item.items()
                        if k in ignore:
                            continue
                        if type(v) == list:
                            screen.append(etree.Element(k))
                            # breakpoint()
                        else:
                            if k == "label":
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
        """
        Get the list of choices labels.
        """
        for key, value in self.config["choices"].items():
            index = 0
            if type(value) == list:
                for label in value:
                    if type(label) == str:
                        element.append(self.make_text(label, f"{key}-{index}"))
                    else:
                        [[k, v]] = label.items()
                        element.append(self.make_text(v, f"{key}-{index}"))
                    index += 1

    def set_choices(self,
                    element: etree.Element,
                    ):
        """
        Get the list of choices labels.
        """
        for key, value in self.config["choices"].items():
            index = 0
            if type(value) == str:
                element.append(self.make_text("-", f"{key}-{index}"))
            else:
                for item in value:
                    element.append(self.make_text("-", f"{key}-{index}"))
                    index += 1

    def get_questions(self,
                    element: etree.Element,
                    ):
        """
        Get all the questions from the config file.
        """
        screen = dict()
        for group, values in self.config["survey"]["groups"].items():
            # element.append(self.make_text(values[0]["label"], f"/data/{group}:label"))
            for entry, val in values.items():
                # Groups have a label, but it's not used anywhere.
                print(f"2: {entry}, {val}")
                if entry == "label":
                    continue
                elif type(val) == list:
                    tmp = dict()
                    # Convert the list to a dict
                    for item in val:
                        [[k3, v3]] = item.items()
                        tmp[k3] = v3
                        if v3[:7] == "select_":
                            screen[k3] = f"/data/{entry}"
                        print(f"\t3: {k3}, {v3}")
                        # if k3 != "label":
                        #     continue
                    if tmp["type"] == "geopoint":
                        element.append(self.make_text("-", f"/data/{group}/{val}:hint"))
                    else:
                        if "name" in tmp:
                            element.append(self.make_text(tmp["name"], f"/data/{group}/{val}:label"))
                        else:
                            element.append(self.make_text(entry, f"/data/{group}/{val}:label"))

        for key, value in self.config["questions"].items():
            # index = 0
            if type(value) == list:
                for label in value:
                    if not label:
                        continue
                    [[k, v]] = label.items()
                    if k == "question":
                        if key in screen:
                            element.append(self.make_text(v, f"{screen[key]}/{key}:label"))
                    elif k == "default":
                        self.defaults[key] = v
                    # index += 1

    def make_text(self,
                  entry: str,
                  id: str,
                  ) -> etree.Element:
        """
        Get all the choices from the config file.
        """
        text = etree.Element("text", id=id)
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
            print(f"FIXME1: {k} = {v}")
            if type(v) == list:
                for entry in v:
                    if type(entry) == dict:
                        [[k2, v2]] = entry.items()
                        print(f"FIXME2: {k2} = {v2}")
                        select_one = list()
                        if k2 == "select_one":
                            select_one = v2
                        elif k2 == "select_multiple":
                            # self.select_multiple(v2)
                            pass
                        if type(v2) == list:
                            pass
                        print(f"FIXME1: {k2}, {v2}")
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
