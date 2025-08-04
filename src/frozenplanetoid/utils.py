import argparse
import pathlib
from xml.etree import ElementTree

import yaml


def opml_to_yaml():
    parser = argparse.ArgumentParser()
    parser.add_argument("opml", type=pathlib.Path)
    args = parser.parse_args()

    feeds = []

    opml = ElementTree.parse(args.opml).iter()
    while True:
        try:
            e = next(opml)
        except StopIteration:
            break
        if "xmlUrl" in e.attrib and "title" in e.attrib:
            feeds.append(
                {
                    "categories": [current_category],
                    "rss": e.attrib["xmlUrl"],
                    "title": e.attrib["title"],
                }
            )
        elif "text" in e.attrib:
            current_category = e.attrib["text"]

    print(yaml.dump(feeds))
