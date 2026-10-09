"""Guards for docs/img/screens/ against scripts/take_screenshots.py of the latest app release.

The app takes the screenshots and writes them into a checkout of this repository; its own
tests guard the viewport. That every screenshot is embedded, with its dark twin and alt text,
is tests/test_docs_figures.py's job.
"""

import re
from pathlib import Path

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
