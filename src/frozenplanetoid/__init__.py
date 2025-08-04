import argparse
import pathlib
import yaml

import feedparser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    args = parser.parse_args()
    config = yaml.load(args.config.read_text(), yaml.SafeLoader)
    feeds = config
    for feed in feeds:
        feed = feedparser.parse(feed["rss"])
