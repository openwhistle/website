"""The site and the latest app release share one look and describe one workflow (S-7).

Fonts, favicons, the mark's geometry and DESIGN.md are copies in both repositories; each pair
must be byte-identical (or, for the mark, the same path), or the site and the app drift apart
visually. The admin guide's case statuses are the release's `ReportStatus`. The release is read
by scripts/release_source.py; tests/test_release_source.py pins the comparison on a fixture.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest
import release_source

from tests.test_mark import icons

ROOT = Path(__file__).resolve().parents[1]
FONTS = [
    "sora-latin-400-normal.woff2",
    "sora-latin-500-normal.woff2",
    "sora-latin-600-normal.woff2",
    "sora-latin-700-normal.woff2",
    "JetBrainsMono-Regular.woff2",
    "JetBrainsMono-Bold.woff2",
    "sora-LICENSE",
    "jetbrains-mono-LICENSE",
]
# this repository's file -> the release's
SHARED = {
    **{f"docs/fonts/{name}": f"app/static/fonts/{name}" for name in FONTS},
    **{f"docs/{name}": f"app/static/{name}" for name in ("favicon.svg", "favicon.ico")},
    "docs/apple-touch-icon.png": "app/static/apple-touch-icon.png",
    "DESIGN.md": "DESIGN.md",
}


@pytest.mark.parametrize(("ours", "theirs"), SHARED.items(), ids=list(SHARED))
def test_every_shared_file_is_the_releases(ours: str, theirs: str) -> None:
    assert not release_source.differs(ROOT / ours, theirs), (
        f"{ours} differs from {theirs} of {release_source.tag()}: copy the newer one across"
    )


def test_the_mark_is_the_releases_geometry() -> None:
    assert icons.MARK == release_source.constant("scripts/render_icons.py", "MARK")


# One clause per status the case can leave: "From a it goes to b or c", "from a to b, c or back to
# d", "a closed case can reopen to b". The figure's text alternative is the guide's status list.
_CLAUSE = re.compile(r"(?:[Ff]rom (\w+)(?: it goes)? to|[Aa] (\w+) case can reopen to) ([^;.]+)")
_TARGETS = re.compile(r",\s*|\s+or\s+")


def _described(alt: str) -> tuple[set[str], set[tuple[str, str]]]:
    """(the statuses, the transitions) a lifecycle text alternative describes."""
    edges = set()
    for found in _CLAUSE.finditer(alt):
        source = found.group(1) or found.group(2)
        for target in _TARGETS.split(found.group(3).strip()):
            edges.add((source, target.removeprefix("back to ").strip()))
    first = re.search(r"a submitted report is (\w+)\.", alt)
    named = {first.group(1)} if first else set()
    return named | {s for edge in edges for s in edge}, edges


def test_the_lifecycle_text_is_parsed_clause_by_clause() -> None:
    statuses, edges = _described(
        "a submitted report is new. From new it goes to open or done; from open to waiting, "
        "done or back to new; a done case can reopen to open. New carries a deadline."
    )
    assert statuses == {"new", "open", "done", "waiting"}
    assert edges == {
        ("new", "open"),
        ("new", "done"),
        ("open", "waiting"),
        ("open", "done"),
        ("open", "new"),
        ("done", "open"),
    }


def test_the_admin_guide_describes_exactly_the_report_statuses_and_transitions() -> None:
    """Both themes' text alternative: a status or a transition the release dropped, renamed or
    added — with an underscore or without — fails."""
    guide = (ROOT / "docs/en/docs/admin/index.html").read_text(encoding="utf-8")
    alts = re.findall(r'src="/img/diagrams/case-lifecycle-(light|dark)\.svg" alt="([^"]+)"', guide)
    assert sorted(theme for theme, _ in alts) == ["dark", "light"], alts
    statuses = set(release_source.enum_values("app/models/report.py", "ReportStatus"))
    transitions = release_source.constant("app/models/report.py", "STATUS_TRANSITIONS")
    allowed = {(a, b) for a, targets in transitions.items() for b in targets}
    for theme, alt in alts:
        named, edges = _described(html.unescape(alt))
        assert named == statuses, (theme, {"missing": statuses - named, "stray": named - statuses})
        assert edges == allowed, (theme, {"missing": allowed - edges, "stray": edges - allowed})
