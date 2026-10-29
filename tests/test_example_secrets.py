"""No key the site shows as an example may pass the release's own length check.

The Quick Start once hard-coded a 48-character SECRET_KEY: an install that skipped the edit ran
with a key anyone could read. The app's own example files: the same guard in
openwhistle/OpenWhistle.
"""

import html
import re
from pathlib import Path

import release_source

ROOT = Path(__file__).parents[1]
# KEY=value or KEY: value, read as the reader sees it: tags stripped, entities decoded. It used to
# read two named pages with a pattern each, so the other pages showing a key went unchecked.
ASSIGNMENT = re.compile(r"\b(SECRET_KEY|ENCRYPTION_KEY)\b[ \t]*[=:][ \t]*([^\s,;]*)")


def _shown(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def test_no_example_key_on_the_site_passes_the_length_check() -> None:
    minimum = release_source.constant("app/config.py", "_MIN_SECRET_KEY_LEN")
    pages = [
        p
        for p in (ROOT / "docs").rglob("*")
        if p.suffix in {".html", ".md"} and "/docs/_" not in p.as_posix()
    ]
    found = []
    for page in pages:
        for name, value in ASSIGNMENT.findall(_shown(page.read_text(encoding="utf-8"))):
            found.append(name)
            assert len(value) < minimum, (page.relative_to(ROOT).as_posix(), name, value)
    assert "SECRET_KEY" in found, "no example SECRET_KEY found — the check reaches nothing"


def test_a_key_inside_markup_is_read_as_shown() -> None:
    shown = _shown('<span class="k">SECRET_KEY</span>=<span>&quot;abc&quot;</span>')
    assert ASSIGNMENT.findall(shown) == [("SECRET_KEY", '"abc"')]
