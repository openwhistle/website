"""No key the site shows as an example may pass the release's own length check.

The Quick Start once hard-coded a 48-character SECRET_KEY: an install that skipped the edit ran
with a key anyone could read. The app's own example files: the same guard in
openwhistle/OpenWhistle.
"""

import re
from pathlib import Path

import release_source

ROOT = Path(__file__).parents[1]
KEYS = ("SECRET_KEY", "ENCRYPTION_KEY")


def test_no_example_key_on_the_site_passes_the_length_check() -> None:
    minimum = release_source.constant("app/config.py", "_MIN_SECRET_KEY_LEN")
    found = []
    sources = {
        "docs/de/blog/interne-meldestelle-einrichten.html": r"^({k})=(.*)$",
        "docs/en/docs/install/index.html": r"({k})</span>=([^\n<]*)",
    }
    for path, pattern in sources.items():
        text = (ROOT / path).read_text()
        for key in KEYS:
            for name, value in re.findall(pattern.format(k=key), text, re.M):
                found.append(name)
                assert len(value.strip()) < minimum, (path, name, value)
    assert "SECRET_KEY" in found, "no example SECRET_KEY found — the check reaches nothing"
