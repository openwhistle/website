"""The site names every interface language of the latest app release (`_SUPPORTED` of its
app/i18n.py, parsed). The locale files themselves are checked in openwhistle/OpenWhistle."""

from __future__ import annotations

import re
from pathlib import Path

import release_source

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _supported() -> set[str]:
    return set(release_source.constant("app/i18n.py", "_SUPPORTED"))


def test_the_site_counts_every_supported_language() -> None:
    """A new locale reaches the site's count (PR #126: the home page still said "4 languages")."""
    count = len(_supported())
    assert f"{count} languages:" in (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert f"{count} Sprachen:" in (DOCS / "de" / "index.html").read_text(encoding="utf-8")


# Each locale's name in the site's English and German prose. A new locale must add its names here.
_LANGUAGE_NAMES = {
    "en": ("English", "Englisch"),
    "de": ("German", "Deutsch"),
    "fr": ("French", "Französisch"),
    "es": ("Spanish", "Spanisch"),
    "pt-br": ("Brazilian Portuguese", "Portugiesisch"),
}

# Every passage of the site that lists the interface languages: (page, sentence pattern, how many).
_LANGUAGE_LISTS = [
    ("en/index.html", r"The interface is in (.*?)\.", 2),  # FAQ and its FAQPage JSON-LD
    ("en/index.html", r"\d+ languages: (.*?)</td>", 1),
    ("de/index.html", r"Die Oberfläche gibt es auf (.*?)\.", 2),
    ("de/index.html", r"\d+ Sprachen: (.*?)</td>", 1),
    ("en/contribute/index.html", r"The app speaks (.*?)\.", 1),
    ("de/mitmachen/index.html", r"Die App spricht (.*?)\.", 1),
]


def test_every_site_language_list_names_every_locale() -> None:
    """The count row was guarded; the lists beside it were not, and the Contribute pages kept
    naming four languages after Spanish arrived."""
    assert set(_LANGUAGE_NAMES) == _supported()
    stale = []
    for name, pattern, count in _LANGUAGE_LISTS:
        lists = re.findall(pattern, (DOCS / name).read_text(encoding="utf-8"))
        assert len(lists) == count, (name, pattern, lists)
        german = name.startswith("de/")
        for listed in lists:
            stale += [
                (name, n[german]) for n in _LANGUAGE_NAMES.values() if n[german] not in listed
            ]
    assert not stale, stale
