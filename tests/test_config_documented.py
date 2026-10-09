"""Every setting of the latest release is documented, once (S-5: its config.py, parsed)."""

from __future__ import annotations

import re
from pathlib import Path

import release_source
import yaml

from tests.built_site import page

ROOT = Path(__file__).parents[1]
CONFIG = yaml.safe_load((ROOT / "docs/_data/config.yml").read_text(encoding="utf-8"))
DOCUMENTED = [s["name"] for g in CONFIG["groups"] for s in g["settings"]]


def test_config_yml_lists_every_setting_once_and_nothing_else() -> None:
    settings = set(release_source.settings())
    assert len(DOCUMENTED) == len(set(DOCUMENTED)), [
        n for n in DOCUMENTED if DOCUMENTED.count(n) > 1
    ]
    assert set(DOCUMENTED) == settings, {
        "undocumented": sorted(settings - set(DOCUMENTED)),
        "stale": sorted(set(DOCUMENTED) - settings),
    }


def test_the_configuration_page_shows_every_setting() -> None:
    rows = re.findall(r'<code class="env-key">([A-Z0-9_]+)</code>', page("/en/docs/configuration/"))
    assert sorted(rows) == sorted(DOCUMENTED)


def test_every_group_is_shown_on_the_page_that_explains_it() -> None:
    for group in CONFIG["groups"]:
        if group["id"] == "core":
            continue  # the core settings are the reference itself
        url = group["page"].partition("#")[0]
        rows = re.findall(r'<code class="env-key">([A-Z0-9_]+)</code>', page(url))
        assert {s["name"] for s in group["settings"]} <= set(rows), (group["id"], url)
