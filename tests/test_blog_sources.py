"""Every blog article backs its claims with a numbered source list, each source with the date it
was retrieved. The comparison article names competitors and their prices, the guides cite the
HinSchG, the GDPR and the EU directive: a claim the reader cannot check against a dated source is
a claim a competitor can challenge. Before 2026-10-27 four of fourteen articles named a retrieval
date, and most legal citations linked nothing.

The shape, German and English alike:

    ... nach § 12 Abs. 2 HinSchG <a class="cite" href="#q1">[1]</a>.
    <section class="sources" aria-labelledby="sources-title">
      <h2 id="sources-title">Quellen</h2>
      <ol>
        <li id="q1"><a href="https://...">Title</a>, publisher. Abgerufen am 27. Oktober 2026.</li>
      </ol>
    </section>
"""

from __future__ import annotations

import datetime as dt
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
ARTICLES = sorted(p for p in (ROOT / "docs").glob("*/blog/*.html") if p.name != "index.html")
# The project's own site and repositories: where to go next, not evidence.
OWN_HOSTS = re.compile(
    r"^https://(?:(?:[a-z0-9-]+\.)?openwhistle\.net(?:/|$)|github\.com/openwhistle/)"
)
MONTHS = {
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
    "en": "January February March April May June July August September October November December",
}
RETRIEVED = {
    "de": re.compile(r"Abgerufen am (\d{1,2})\.(?:\s|&nbsp;)(\w+) (\d{4})\.$"),
    "en": re.compile(r"Retrieved (\d{1,2}) (\w+) (\d{4})\.$"),
}
TITLE = {"de": "Quellen", "en": "Sources"}
# EUR-Lex serves one act per language; the twins cite the same act in their own.
_EUR_LEX_LANG = re.compile(r"/legal-content/(?:DE|EN)/")


class _Article(HTMLParser):
    """Splits an article into its body links, its citations and its source entries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.body_links: list[str] = []
        self.cites: list[str] = []
        self.sections = 0
        self.title = ""
        self.entries: list[dict[str, object]] = []
        self._in_sources = False
        self._in_title = False
        self._entry: dict[str, object] | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "section" and "sources" in (a.get("class") or "").split():
            self.sections += 1
            self._in_sources = True
            self._depth = 0
        elif tag == "section" and self._in_sources:
            self._depth += 1
        if self._in_sources:
            if tag == "h2":
                self._in_title = True
            elif tag == "li":
                self._entry = {"id": a.get("id"), "links": [], "text": ""}
            elif tag == "a" and self._entry is not None:
                self._entry["links"].append(a.get("href") or "")  # type: ignore[union-attr]
            return
        href = a.get("href") or ""
        if tag == "a" and "cite" in (a.get("class") or "").split():
            self.cites.append(href)
        elif tag == "a" and href.startswith("http") and not OWN_HOSTS.match(href):
            self.body_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_sources:
            return
        if tag == "h2":
            self._in_title = False
        elif tag == "li" and self._entry is not None:
            self._entry["text"] = " ".join(str(self._entry["text"]).split())
            self.entries.append(self._entry)
            self._entry = None
        elif tag == "section":
            if self._depth:
                self._depth -= 1
            else:
                self._in_sources = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._entry is not None:
            self._entry["text"] = str(self._entry["text"]) + data


def _meta(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def _parse(text: str) -> _Article:
    parser = _Article()
    parser.feed(text)
    return parser


def problems(text: str, lang: str, modified: dt.date) -> list[str]:
    """What is wrong with one article's sources; empty when nothing is."""
    art = _parse(text)
    if art.sections != 1:
        return [f"{art.sections} source sections, want 1"]
    found: list[str] = []
    if art.title.strip() != TITLE[lang]:
        found.append(f"title {art.title.strip()!r}, want {TITLE[lang]!r}")
    ids = [e["id"] for e in art.entries]
    if not ids or ids != [f"q{n}" for n in range(1, len(ids) + 1)]:
        found.append(f"source ids {ids}, want q1..qN")
    urls: list[str] = []
    months = MONTHS[lang].split()
    for e in art.entries:
        links = [h for h in e["links"] if h.startswith("http")]  # type: ignore[union-attr]
        if len(links) != 1:
            found.append(f"{e['id']}: {len(links)} links, want 1")
        urls += links
        m = RETRIEVED[lang].search(str(e["text"]))
        if not m or m.group(2) not in months:
            found.append(f"{e['id']}: no retrieval date at the end: {e['text']!r}")
            continue
        day = dt.date(int(m.group(3)), months.index(m.group(2)) + 1, int(m.group(1)))
        if day > modified:
            found.append(f"{e['id']}: retrieved {day}, after the article's modified {modified}")
    for href in art.body_links:
        if href not in urls:
            found.append(f"body link not in the sources: {href}")
    for cite in art.cites:
        if cite.removeprefix("#") not in ids:
            found.append(f"citation {cite} names no source")
    for source_id in ids:
        if f"#{source_id}" not in art.cites:
            found.append(f"{source_id} is never cited")
    return found


@pytest.mark.parametrize("path", ARTICLES, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_every_article_cites_dated_sources(path: Path) -> None:
    lang = path.parent.parent.name
    modified = dt.date.fromisoformat(str(_meta(path)["modified"]))
    assert problems(path.read_text(encoding="utf-8"), lang, modified) == []


def test_german_and_english_twins_cite_the_same_sources() -> None:
    by_key: dict[str, dict[str, list[str]]] = {}
    for path in ARTICLES:
        art = _parse(path.read_text(encoding="utf-8"))
        urls = [
            _EUR_LEX_LANG.sub("/legal-content/XX/", str(link))
            for e in art.entries
            for link in e["links"]  # type: ignore[attr-defined]
        ]
        by_key.setdefault(str(_meta(path)["translation_key"]), {})[path.parent.parent.name] = urls
    differ = {k: v for k, v in by_key.items() if v.get("de") != v.get("en")}
    assert not differ, differ


GOOD = (
    '<p>Ab 50 <a class="cite" href="#q1">[1]</a>.</p>'
    '<section class="sources" aria-labelledby="sources-title"><h2 id="sources-title">Quellen</h2>'
    '<ol><li id="q1"><a href="https://example.org/a">A</a>, X.'
    " Abgerufen am 27.&nbsp;Oktober 2026.</li>"
    "</ol></section>"
)
DAY = dt.date(2026, 10, 27)


def test_a_good_article_passes() -> None:
    assert problems(GOOD, "de", DAY) == []


@pytest.mark.parametrize(
    ("mutate", "lang", "day", "complaint"),
    [
        (lambda t: t.replace("Abgerufen am 27.&nbsp;Oktober 2026.", ""), "de", DAY, "no retrieval"),
        (lambda t: t, "de", dt.date(2026, 10, 26), "after the article's modified"),
        (lambda t: t.replace('href="#q1"', 'href="#q2"'), "de", DAY, "names no source"),
        (lambda t: t.replace('<a class="cite" href="#q1">[1]</a>', ""), "de", DAY, "never cited"),
        (lambda t: t.replace('id="q1"', 'id="q2"'), "de", DAY, "want q1..qN"),
        (lambda t: "<a href='https://x.org/'>x</a>" + t, "de", DAY, "not in the sources"),
        (lambda t: t.replace('class="sources"', 'class="refs"'), "de", DAY, "0 source sections"),
        (lambda t: t, "en", DAY, "want 'Sources'"),
    ],
)
def test_each_rule_fails_on_its_breach(
    mutate: object, lang: str, day: dt.date, complaint: str
) -> None:
    found = problems(mutate(GOOD), lang, day)  # type: ignore[operator]
    assert any(complaint in line for line in found), found


def test_own_links_need_no_source() -> None:
    text = GOOD.replace("<p>", '<p><a href="https://demo.openwhistle.net">Demo</a> ')
    assert problems(text, "de", DAY) == []


_UPDATED = {
    "de": re.compile(r"<span>Aktualisiert am (\d{1,2})\. (\w+) (\d{4})</span>"),
    "en": re.compile(r"<span>Updated (\d{1,2}) (\w+) (\d{4})</span>"),
}


@pytest.mark.parametrize("path", ARTICLES, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_the_visible_update_date_is_the_modified_date(path: Path) -> None:
    """The comparison said "Updated 11 October" while its feed and JSON-LD said the 12th."""
    lang = path.parent.parent.name
    m = _UPDATED[lang].search(path.read_text(encoding="utf-8"))
    assert m, "no update line in the article meta"
    day = dt.date(int(m.group(3)), MONTHS[lang].split().index(m.group(2)) + 1, int(m.group(1)))
    assert day == dt.date.fromisoformat(str(_meta(path)["modified"]))


def test_the_compare_page_dates_its_table_by_the_day_its_sources_were_read() -> None:
    """/en/compare/ said "As of 2026-09" above facts read on 2026-09-27; a re-check that moves one
    date and not the other states a table as current that nobody re-read."""
    text = (ROOT / "docs" / "en" / "compare" / "index.html").read_text(encoding="utf-8")
    (as_of,) = re.findall(r'<th scope="col">As of (\d{4}-\d{2}-\d{2})</th>', text)
    (lead,) = re.findall(r"retrieved on (\d{1,2} \w+ \d{4})\. Where a source", text)
    (read,) = re.findall(r"<p>All retrieved on (\d{1,2} \w+ \d{4})\.", text)
    assert lead == read
    day, month, year = read.split()
    months = MONTHS["en"].split()
    assert as_of == f"{year}-{months.index(month) + 1:02d}-{int(day):02d}"


def _shape(text: str) -> tuple[int, ...]:
    body = text.split("---", 2)[2]
    return tuple(len(re.findall(p, body)) for p in ("<h2", "<tr", "<li", 'class="cite"', "<figure"))


def test_german_and_english_twins_have_the_same_shape() -> None:
    """Same sections, table rows, list items, citations and figures: a fact added to one language
    and not the other shows up here. The English twins once lagged the German ones by two weeks."""
    shapes: dict[str, dict[str, tuple[int, ...]]] = {}
    for path in ARTICLES:
        text = path.read_text(encoding="utf-8")
        shapes.setdefault(str(_meta(path)["translation_key"]), {})[path.parent.parent.name] = (
            _shape(text)
        )
    differ = {k: v for k, v in shapes.items() if v.get("de") != v.get("en")}
    assert not differ, differ
