"""No published page promises a cipher the app does not use (v2.1.0 bug bounty).

The README half stays in openwhistle/OpenWhistle.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_no_published_page_calls_fernet_aes_256() -> None:
    """Fernet is AES-128-CBC with HMAC-SHA256. The security policy and the
    DPA template promised AES-256 and a SECRET_KEY-derived master key."""
    pages = [
        *(p for p in (ROOT / "docs").rglob("*.md") if "/docs/_" not in p.as_posix()),
        *(p for p in (ROOT / "docs").rglob("*.html") if "/docs/_" not in p.as_posix()),
    ]
    # The changelog page's source carries no notes: it renders CHANGELOG.md
    # (past releases as written, not rewritten) at build time, and is not read here.
    offenders = [p.name for p in pages if re.search(r"AES-?256", p.read_text())]
    assert not offenders
