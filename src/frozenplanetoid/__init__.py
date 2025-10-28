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
    def date(self):
        return self.e.updated_parsed

    def html_content(self, base_header_level):
        if hasattr(self.e, "content"):
            content = self.e.content
        elif hasattr(self.e, "summary_detail"):
            content = [self.e.summary_detail]
        else:
            return None
        html = [c for c in content if c.type in ("text/html", "application/xhtml+xml")]
        if len(html) != 1:
            return None
        html = SANITIZER.sanitize(html[0].value)
        if not html:
            return None
        html = lxml.html.fromstring(html)

        min_header_level = None
        max_header_level = None

        HEADERS = ("h1", "h2", "h3", "h4", "h5", "h6")
        for fragment in html.iter():
            if fragment.tag not in HEADERS:
                continue
            header_level = HEADERS.index(fragment.tag) + 1
            if not min_header_level or header_level < min_header_level:
                min_header_level = header_level
            if not max_header_level or header_level > max_header_level:
                max_header_level = header_level

        for fragment in html.iter():
            if fragment.tag not in HEADERS:
                continue
            header_level = HEADERS.index(fragment.tag) + 1
            new_level = min(header_level - min_header_level + base_header_level, 6)
            fragment.tag = f"h{new_level}"
        return lxml.html.tostring(html).decode("utf8")

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
                            f" ({self.feed.feed.title})",
                        ),
                        htmlgenerator.mark_safe(self.html_content(3) or ""),
                    )
                )
            )
        )


def render(title, feeds):
    content = []

    index = []

    for i, f in enumerate(feeds):
        if i != 0:
            index.append(", ")

        index.append(
            htmlgenerator.A(
                f.feed.title or "?",
                href=f.feed.link,
            )
        )
        index.append(f" ({len(f.entries)})")

    content.append(htmlgenerator.P(*index))

    entries = []
    for f in feeds:
        entries += [Entry(e, f) for e in f.entries]
    entries = reversed(sorted(entries, key=lambda e: e.date))

    previous_date = None

    for entry in entries:
        entry_date = datetime.date(*entry.date[0:3])
        if entry_date != previous_date:
            content.append(htmlgenerator.H1(str(entry_date)))
        content.append(entry.as_html())
        previous_date = entry_date

    return html(title, *(content))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="-")
    parser.add_argument("--title", type=str, default="Frozen Planetoid")
    parser.add_argument("feed", nargs="*")

    args = parser.parse_args()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:

        def _parse(f):
            result = feedparser.parse(f)
            if hasattr(result, "bozo_exception") and not isinstance(
                result.bozo_exception, feedparser.exceptions.CharacterEncodingOverride
            ):
                raise Exception(f"Error parsing {f}", result.bozo_exception)
            return result

        feeds = list(executor.map(_parse, args.feed))

    output = render(args.title, feeds)

    if args.output == "-":
        print(output, end="")
    else:
        pathlib.Path(args.output).write_text(output)


def html(title, *body):
    return lxml.html.tostring(
        lxml.html.fromstring(
            htmlgenerator.render(
                htmlgenerator.HTML(
                    htmlgenerator.HEAD(
                        htmlgenerator.TITLE(title),
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
                              /* from Mozilla reader mode */
                              line-height: 1.6em;
                              font-size: 20px;
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
        doctype="<!DOCTYPE html>",
    ).decode("utf8")
