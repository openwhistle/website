"""The release Chrome check's page list (docs-tech/local-review.md) names every built page.

The app's pages and templates: the same guard in openwhistle/OpenWhistle.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.built_site import built, pages

ROOT = Path(__file__).parents[1]


def _docs_html_pages() -> set[str]:
    """The URL of every built page: a folder's index.html is served at the folder."""
    return {"/" + p.relative_to(built()).as_posix().removesuffix("index.html") for p in pages()}


_BACKTICK_TOKEN = re.compile(r"`([^`]+)`")


def _matrix_table_tokens() -> set[str]:
    """Every backtick-quoted token found only on genuine markdown table rows
    (a line starting with '|') in the page matrix — not a stray backtick
    path in running prose elsewhere in the file (an absolute filesystem
    path, a shell command). Deliberately '|', not '| `': some rows use a
    non-path placeholder in the first cell for a POST-rendered page, with
    the real path/template token in a later cell instead."""
    text = (ROOT / "docs-tech/local-review.md").read_text()
    tokens: set[str] = set()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        tokens.update(_BACKTICK_TOKEN.findall(line))
    return tokens


def test_local_review_page_matrix_covers_every_docs_site_page() -> None:
    pages = _docs_html_pages()
    assert len(pages) >= 9, f"only {len(pages)} built pages found — the build may be broken"
    missing = pages - _matrix_table_tokens()
    assert not missing, f"docs-tech/local-review.md is missing site page(s): {sorted(missing)}"
