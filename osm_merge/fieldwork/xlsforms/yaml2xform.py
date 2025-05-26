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
        lang = etree.Element("translation", lang="English(en)")
        # first is all the labels of the choices
        self.get_questions(lang)
        itext.append(lang)
        model.append(itext)

        # Then the instances
        self.add_instance(model)
        # then they get a blank default as a placeholer
        # self.set_choices(model)
        self.add_nodeset(model)
        # self.get_choices(model)
        # self.add_geopoint(lang)
        # self.add_choices(model)

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
                            if type(newval) == dict:
                                [[k2, v2]] = newval.items()
                                if type(v2) == str:
                                    self.data[key][k].update(newval)
                                elif type(v2) == list:
                                    self.data[key][k][k2] = dict()
                                    for xxx in v2:
                                        [[k3, v3]] = xxx.items()
                                        if type(v3) == list:
                                            self.data[key][k][k2][k3] = dict()
                                            for foo in v3:
                                                self.data[key][k][k2][k3].update(foo)
                                            pass
                                        else:
                                            self.data[key][k][k2].update(xxx)
                    else:
                        log.error(f"{type(v)} is not suported.")

        # breakpoint()
        return self.data

    def lookup_value(self,
                     value: str,
                     ) -> str:
        """
        """
        for group, entry in self.config["survey"]["groups"].items():
            return f"/data/{group}/{entry[value]["name"]}"

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
                    continue
                if v2["type"][:7] == "select_":
                    select = etree.Element("select1",
                                           appearance=v2["appearance"],
                                           ref=f"/data/{k}/{v2["name"]}")
                    label = etree.Element("label",
                                          ref=f"jr_itext('/data/{k}/{v2["name"]}:label')")
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

        punc = ("=")
        # Get the list of groups
        for k, v in self.config["survey"]["groups"].items():
            for k2, v2 in v.items():
                if type(v2) == str:
                    continue
                if "name" in v2:
                    defaults["nodeset"] = f"/data/{k}/{v2["name"]}"
                    defaults["type"] = v2["type"]
                else:
                    defaults["nodeset"] = f"/data/{k}/{k2}"
                for k3, v3 in self.config["questions"].items():
                    if not v3:
                        continue
                    # print(f"FIXME: {k3} = {v3.keys()}")
                    if "required" in v3 or "readonly" in v3:
                        defaults[k2] = "true()"
                    if "relevantX" in v3:
                        value = str()
                        relevant = v3["relevant"]
                        if relevant.find(" or ") > 0:
                            for i in relevant.split(" or "):
                                for test in punc:
                                    if i.find(test) > 0:
                                        tmp = i.split(test)
                                        xpath = self.lookup_value(tmp[0])
                                        value += f"{xpath} {test}'{tmp[1]}' or "
                                        break
                        if relevant.find(" and ") > 0:
                            for i in relevant.split(" and "):
                                for test in punc:
                                    if i.find(test) > 0:
                                        tmp = i.split(test)
                                        xpath = self.lookup_value(tmp[0])
                                        value += f"{xpath} {test}'{tmp[1]}' and )"
                                        break
                        # Drop the trailing conditional
                        if value[-1:] == " ":
                            pos = value[:-1].rfind(" ")
                        defaults[k3] = value[:pos]
                    else:
                        if "type" in v3:
                            defaults["type"] = v3["type"]
                        # breakpoint()
                bind = etree.Element("bind")
                for key, value in defaults.items():
                    bind.set(key, value)
                    element.append(bind)

            bind = etree.Element("bind",
                                 jr_preload="uid",
                                 readonly="true()",
                                 type="string",
                                 nodeset="/data/meta/instanceID",
                                 )
            element.append(bind)
            bind = etree.Element("odk_setgeopoint",
                                 event="odk-instance-first-load",
                                 ref="/data/warmup",
                                 )
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
            instance = etree.Element("instance")
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

        instance = etree.Element("instance")
        # ignore = ("geopoint", "geotrace", "image", "text", "select_one", "select_multiple")
        ignore = ("geopoint", "geotrace", "image", "text")
        for group, values in self.config["survey"]["groups"].items():
            screen = etree.Element(group)
            for key, value in values.items():
                # screen = etree.Element(key)
                data.append(screen)
                # ignore the attributes for the group
                if type(value) == str:
                    continue
                elif type(value) == dict:
                    if "name" in value:
                        name = etree.Element(value["name"])
                    else:
                        name = etree.Element(key)
                    if "default" in self.config["questions"][key]:
                        name.text = self.config["questions"][key]["default"]
                    screen.append(name)

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
            element.append(self.make_text(values["label"], f"/data/{group}:label"))
        for key, value in self.config["questions"].items():
            print(key, value)
            element.append(self.make_text(value["question"],
                                f"/data/{group}/{key}:label"))
                # if "default" in value:
                #     self.defaults[key] = value["default"]
                #     # index += 1

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

    # def parse_config(self):
    #     """
    #     Parse the YAML config file.
    #     """
    #     for item in self.config["survey"]["groups"]:
    #         [[k, v]] = item.items()
    #         print(f"FIXME1: {k} = {v}")
    #         if type(v) == list:
    #             for entry in v:
    #                 if type(entry) == dict:
    #                     [[k2, v2]] = entry.items()
    #                     print(f"FIXME2: {k2} = {v2}")
    #                     select_one = list()
    #                     if k2 == "select_one":
    #                         select_one = v2
    #                     elif k2 == "select_multiple":
    #                         # self.select_multiple(v2)
    #                         pass
    #                     if type(v2) == list:
    #                         pass
    #                     print(f"FIXME1: {k2}, {v2}")
    #                 else:
    #                     print(f"FIXME2: {k} {v}")

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
