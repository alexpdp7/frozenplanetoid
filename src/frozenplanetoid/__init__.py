import argparse
import dataclasses
import pathlib
import pprint
import yaml

import feedparser


class Feed:
    def __init__(self, d):
        self.d = d

    @property
    def rss(self):
        return self.d["rss"]

    def load(self):
        # self.parsed = feedparser.parse(self.rss)
        pass

    def __repr__(self):
        return f"Feed({self.d['rss']})"


@dataclasses.dataclass
class Category:
    children_categories: dict[str, "Categories"]
    feeds: list[Feed]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    args = parser.parse_args()
    config = yaml.load(args.config.read_text(), yaml.SafeLoader)
    feeds = config

    root_category = Category(children_categories={}, feeds=[])

    for feed in feeds:
        feed = Feed(feed)
        feed.load()

        for feed_category in feed.d["categories"]:
            category_pointer = root_category
            for feed_category_path in feed_category.split("/"):
                if feed_category_path not in category_pointer.children_categories:
                    category_pointer.children_categories[feed_category_path] = Category(children_categories={}, feeds=[])
                category_pointer = category_pointer.children_categories[feed_category_path]
                category_pointer.feeds.append(feed)
    pprint.pprint(root_category)
