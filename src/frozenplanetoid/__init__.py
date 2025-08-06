import argparse
import concurrent.futures
import dataclasses
import datetime
import pathlib
import shutil
import yaml

import feedparser
import htmlgenerator
import html_sanitizer


SANITIZER = html_sanitizer.Sanitizer()


class Feed:
    def __init__(self, d):
        self.d = d

    @property
    def rss(self):
        return self.d["rss"]

    def load(self):
        print(f"loading {self}")
        self.parsed = feedparser.parse(self.rss)

    def __repr__(self):
        return f"Feed({self.d['rss']})"


class Entry:
    def __init__(self, e, feed):
        self.e = e
        self.feed = feed

    @property
    def title(self):
        return self.e.title

    @property
    def link(self):
        return self.e.link

    @property
    def published_parsed(self):
        return self.e.published_parsed

    def html_content(self):
        if not hasattr(self.e, "content"):
            return None
        html = [
            c
            for c in self.e.content
            if c.type in ("text/html", "application/xhtml+xml")
        ]
        if len(html) != 1:
            return None
        return SANITIZER.sanitize(html[0].value)

    def as_html(self):
        return htmlgenerator.BaseElement(
            htmlgenerator.H2(
                htmlgenerator.A(
                    self.title,
                    href=self.link,
                ),
                f" ({self.feed.parsed.feed.title})",
                _class="entry_header",
            ),
            htmlgenerator.mark_safe(self.html_content() or ""),
        )


@dataclasses.dataclass
class Category:
    children_categories: dict[str, "Categories"]
    feeds: list[Feed]
    name: str
    parent: "Category"

    def as_list_item(self):
        if self.parent is None:
            body = "*"
        else:
            body = htmlgenerator.A(
                f"{self.name} ({len(self.feeds)})",
                href=f"{self.slug}.html",
            )
        return htmlgenerator.LI(
            body,
            htmlgenerator.UL(
                *[c.as_list_item() for _, c in sorted(self.children_categories.items())]
            ),
        )

    @property
    def slug(self):
        if not self.parent:
            return ""
        if not self.parent.parent:
            return f"{self.parent.slug}--{self.name}"[2:]
        return f"{self.parent.slug}--{self.name}"

    def render(self, output):
        entries = []
        for f in self.feeds:
            try:
                [e.published_parsed for e in f.parsed.entries]
            except:
                print(f)
                continue
            entries += [Entry(e, f) for e in f.parsed.entries]
        entries = reversed(sorted(entries, key=lambda e: e.published_parsed))

        content = []
        previous_date = None

        for entry in entries:
            entry_date = datetime.date(*entry.published_parsed[0:3])
            if entry_date != previous_date:
                content.append(htmlgenerator.H1(str(entry_date)))
            content.append(entry.as_html())
            previous_date = entry_date

        (output / f"{self.slug}.html").write_text(html(*(content)))

        for category in self.children_categories.values():
            category.render(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    config = yaml.load(args.config.read_text(), yaml.SafeLoader)
    feeds = config

    with concurrent.futures.ThreadPoolExecutor() as executor:

        def _load(feed):
            feed = Feed(feed)
            feed.load()
            return feed

        feeds = executor.map(_load, feeds)

    root_category = Category(children_categories={}, feeds=[], name="*", parent=None)

    for feed in feeds:
        for feed_category in feed.d["categories"]:
            category_pointer = root_category
            for feed_category_path in feed_category.split("/"):
                if feed_category_path not in category_pointer.children_categories:
                    category_pointer.children_categories[feed_category_path] = Category(
                        children_categories={},
                        feeds=[],
                        name=feed_category_path,
                        parent=category_pointer,
                    )
                category_pointer = category_pointer.children_categories[
                    feed_category_path
                ]
                category_pointer.feeds.append(feed)

    output = args.output
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()

    (output / "index.html").write_text(
        html(htmlgenerator.UL(root_category.as_list_item()))
    )

    for _, category in root_category.children_categories.items():
        category.render(output)


def html(*body):
    return htmlgenerator.render(
        htmlgenerator.HTML(
            htmlgenerator.HEAD(
                htmlgenerator.STYLE("""
                :root {
                  color-scheme: light dark;
                }
                body {
                  max-width: 40em;
                  margin-left: auto;
                  margin-right: auto;
                  padding-left: 2em;
                  padding-right: 2em;
                }
                p, blockquote {
                  /* from Mozilla reader mode */
                  line-height: 1.6em;
                  font-size: 20px;
                }
                img {
                  max-width: 100%;
                  height: auto;
                }
                .entry_header {
                  padding-top: 0.5em;
                  border-top: 0.5em solid black;
                  padding-bottom: 0.5em;
                  border-bottom: 0.5em solid black;
                }
                """),
            ),
            htmlgenerator.BODY(*body),
        ),
        {},
    )
