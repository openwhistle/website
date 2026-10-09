"""Every version string the site publishes is the latest app release's.

One version, written in several places on the site. A release that bumps only some of them
ships docs naming the wrong release. The app's own copies (Chart, CHANGELOG, pyproject, compose,
.env.example): the same guard in openwhistle/OpenWhistle.
"""

import re
from pathlib import Path

import release_source

from tests.built_site import page

ROOT = Path(__file__).parents[1]


def _grab(path: str, pattern: str) -> str | None:
    m = re.search(pattern, (ROOT / path).read_text(), re.M)
    return m.group(1) if m else None


def test_every_published_version_string_matches() -> None:
    found = {
        "docs.html": _grab("docs/en/docs/index.html", r"<strong>v([0-9.]+)</strong>"),
        "index.html": _grab("docs/en/index.html", r"softwareVersion: '?([0-9.]+)"),
        "de/index.html": _grab("docs/de/index.html", r"softwareVersion: '?([0-9.]+)"),
        # The date beside the version is free text; only the version is checked.
        "compare latest release": _grab(
            "docs/en/compare/index.html", r"Latest release</th>\s*<td>([0-9.]+)"
        ),
    }
    v = release_source.app_version()
    assert found == dict.fromkeys(found, v)
    # The images page once named the pin's default in prose and went stale with
    # it; it now says "the release the file shipped with". Keep it so.
    docs = (ROOT / "docs/en/docs/images/index.html").read_text()
    assert "OPENWHISTLE_VERSION" in docs
    assert not re.search(r"OPENWHISTLE_VERSION</code>[^.]*default <code>[0-9.]+", docs)

    # Every visible "Version X.Y.Z" string on both landing pages (hero
    # badge and footer) must also match — the structured-data check above
    # only covers the invisible JSON-LD softwareVersion.
    for url in ("/en/", "/de/"):
        visible = re.findall(r">Version ([0-9.]+)<", page(url))
        assert visible, f"{url}: no visible 'Version X.Y.Z' string found"
        assert visible == [v] * len(visible), (url, visible, v)


def test_the_multi_tenancy_history_stays_at_1_0_0() -> None:
    """A blanket find-replace of the "current version" spots once swept in a historical claim
    ("multi-tenancy has existed since 1.0.0") that must never move with app_version."""
    de_text = (ROOT / "docs/de/index.html").read_text()
    assert "Ab Version 1.0.0 unterstützt OpenWhistle Multi-Tenancy" in de_text
    changelog = release_source.read("CHANGELOG.md")
    v100_section = changelog.split("## [1.0.0]", 1)[1].split("\n## [", 1)[0]
    assert "Multi-tenancy" in v100_section, "multi-tenancy no longer documented under [1.0.0]"
