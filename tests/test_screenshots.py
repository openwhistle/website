"""Guards for docs/img/screens/ against scripts/take_screenshots.py of the latest app release.

The app takes the screenshots and writes them into a checkout of this repository; its own
tests guard the viewport. That every screenshot is embedded, with its dark twin and alt text,
is tests/test_docs_figures.py's job.
"""

import re
from pathlib import Path

import pytest
import release_source

ROOT = Path(__file__).parents[1]
SCREENS_DIR = ROOT / "docs" / "img" / "screens"

_THEMES = ("light", "dark")


def _script_text() -> str:
    return release_source.read("scripts/take_screenshots.py")


def _names_in_script() -> list[str]:
    return re.findall(r'Screenshot\(\s*"([\w-]+)"', _script_text())


def test_every_screenshot_has_a_light_and_dark_twin() -> None:
    files = list(SCREENS_DIR.glob("*.png"))
    assert files, f"no screenshots found in {SCREENS_DIR}"

    names = {re.sub(r"-(light|dark)$", "", p.stem) for p in files}
    missing = [
        f"{name}-{theme}.png"
        for name in sorted(names)
        for theme in _THEMES
        if not (SCREENS_DIR / f"{name}-{theme}.png").exists()
    ]
    assert not missing, f"screenshot missing its light/dark twin: {missing}"


def test_every_name_in_the_script_has_both_files() -> None:
    """Catches a name added, removed or renamed in SCREENSHOTS without
    re-running the script — the list and docs/img/screens/ drift apart
    silently otherwise."""
    names = _names_in_script()
    assert names, "could not parse any Screenshot(...) entries out of scripts/take_screenshots.py"

    missing = [
        f"{name}-{theme}.png"
        for name in names
        for theme in _THEMES
        if not (SCREENS_DIR / f"{name}-{theme}.png").exists()
    ]
    assert not missing, f"scripts/take_screenshots.py lists a name with no rendered file: {missing}"


MARKER = SCREENS_DIR / "_release"  # underscore: the build does not publish it
# The last release whose shots were taken before take_screenshots.py wrote the marker.
_LAST_UNMARKED = (2, 2, 1)


def stale_screens(version: str, marker: str | None) -> str | None:
    """Why the shots are not from `version`, or None. Shots are re-taken for every release:
    the weekly run stayed green on 2.2.0 shots after 2.2.1, nothing compared them."""
    if marker is None:
        if tuple(int(p) for p in version.split(".")) <= _LAST_UNMARKED:
            return None
        return f"{MARKER.name} is missing: re-take the screenshots from {version}"
    if marker.strip() != version:
        return f"screenshots are from {marker.strip()}, latest release {version}: re-take them"
    return None


@pytest.mark.parametrize(
    ("version", "marker", "stale"),
    [
        ("2.2.1", None, False),
        ("2.2.2", None, True),
        ("3.0.0", None, True),
        ("2.2.2", "2.2.2\n", False),
        ("2.2.2", "2.2.1\n", True),
    ],
)
def test_stale_screens_decides(version: str, marker: str | None, stale: bool) -> None:
    assert bool(stale_screens(version, marker)) == stale


def test_the_screenshots_come_from_the_latest_release() -> None:
    marker = MARKER.read_text(encoding="utf-8") if MARKER.exists() else None
    reason = stale_screens(release_source.app_version(), marker)
    assert not reason, reason
