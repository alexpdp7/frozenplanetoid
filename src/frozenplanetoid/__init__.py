import argparse
import concurrent.futures
import datetime
import pathlib
import textwrap

import feedparser
import htmlgenerator
import html_sanitizer
import lxml.html


SANITIZER = html_sanitizer.Sanitizer()


class Feed:
    def __init__(self, url):
        self.url = url

    def load(self):
        print(f"loading {self}")
        self.parsed = feedparser.parse(self.url)

    def __repr__(self):
        return f"Feed({self.url})"


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

    def html_content(self, base_header_level):
        if not hasattr(self.e, "content"):
            return None
        html = [
            c
            for c in self.e.content
            if c.type in ("text/html", "application/xhtml+xml")
        ]
        if len(html) != 1:
            return None
        html = SANITIZER.sanitize(html[0].value)
        html = lxml.html.fromstring(html)

        min_header_level = None
        max_header_level = None

        HEADERS = ("h1", "h2", "h3", "h4", "h5", "h6")
        for fragment in html.iter():
            try:
                header_level = HEADERS.index(fragment.tag) + 1
            except ValueError:
                continue
            if not min_header_level or header_level < min_header_level:
                min_header_level = header_level
            if not max_header_level or header_level > max_header_level:
                max_header_level = header_level

        for fragment in html.iter():
            try:
                header_level = HEADERS.index(fragment.tag) + 1
            except ValueError:
                continue
            new_level = min(header_level - min_header_level + base_header_level, 6)
            fragment.tag = f"h{new_level}"
        return lxml.html.tostring(html)[len("<div>") : -len("</div>")].decode("utf8")

    def as_html(self):
        return htmlgenerator.BaseElement(
            htmlgenerator.ARTICLE(
                htmlgenerator.DETAILS(
                    htmlgenerator.SUMMARY(
                        htmlgenerator.H2(
                            htmlgenerator.A(
                                self.title,
                                href=self.link,
                            ),
                            f" ({self.feed.parsed.feed.title})",
                        ),
                        htmlgenerator.mark_safe(self.html_content(3) or ""),
                    )
                )
            )
        )


def render(feeds, output):
    entries = []
    for f in feeds:
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

    output.write_text(html(*(content)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("feed", nargs="*")

    args = parser.parse_args()

    with concurrent.futures.ThreadPoolExecutor() as executor:

        def _load(feed):
            feed = Feed(feed)
            feed.load()
            return feed

        feeds = executor.map(_load, args.feed)

    render(feeds, args.output)


def html(*body):
    return lxml.html.tostring(
        lxml.html.fromstring(
            htmlgenerator.render(
                htmlgenerator.HTML(
                    htmlgenerator.HEAD(
                        htmlgenerator.STYLE(
                            textwrap.dedent("""
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
                            details {
                              max-height: 30vh;
                              overflow-y: clip
                            }
                            details:open {
                              max-height: none;
                            }
                            details h2 {
                              display: inline;
                            }
                            @media (prefers-color-scheme: light) {
                              article {
                                border: 1px solid black;
                                padding: 1em;
                              }
                            }
                            @media (prefers-color-scheme: dark) {
                              article {
                                border: 1px solid white;
                                padding: 1em;
                              }
                            }
                            """)
                        ),
                    ),
                    htmlgenerator.BODY(*body),
                ),
                {},
            )
        ),
        pretty_print=True,
    ).decode("utf8")
