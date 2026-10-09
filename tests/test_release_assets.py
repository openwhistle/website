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


def test_the_admin_guide_names_exactly_the_report_statuses() -> None:
    """The case-lifecycle figure's text alternative is the guide's status list."""
    guide = (ROOT / "docs/en/docs/admin/index.html").read_text(encoding="utf-8")
    alts = re.findall(r'src="/img/diagrams/case-lifecycle-light\.svg" alt="([^"]+)"', guide)
    assert len(alts) == 1, alts
    alt = html.unescape(alts[0])
    statuses = set(release_source.enum_values("app/models/report.py", "ReportStatus"))
    named = {s for s in statuses if re.search(rf"\b{s}\b", alt)}
    stray = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", alt)) - statuses
    assert named == statuses and not stray, {"missing": statuses - named, "stray": stray}
