"""Browser tests of the site: the built site served locally, or the website container.

uv run pytest tests/e2e -m e2e --browser chromium
"""

from __future__ import annotations

import hashlib
import http.server
import threading
from collections.abc import Generator
from functools import partial
from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.built_site import builder

# The static marketing/docs site is served by its own nginx image. Build it and
# serve the build locally so browser tests against it (layout, theme/nav/scroll-spy
# behaviour) run standalone,
# without the FastAPI app or the review stack. Shared by every test module
# that needs it, so each one does not spin up its own copy of the same fixture.
# Session-wide, built once: pytest reorders parametrised tests across modules, and a
# module fixture rebuilt the whole site at every switch (hours in CI after P3).
_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def docs_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    site = tmp_path_factory.mktemp("site") / "out"
    builder().build(_ROOT / "docs", site)
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


# axe-core is vendored (tests/e2e/vendor/axe.min.js), never fetched. Renovate bumps
# AXE_VERSION; scripts/vendor_axe.py then writes the file and AXE_SHA256.
AXE_VERSION = "4.14.0"
AXE_SHA256 = "20c09fe157a8a34a30e241aaa1fcdade657734f08ab379ecfbeb7d45cc46e878"
_AXE = Path(__file__).parent / "vendor" / "axe.min.js"


@pytest.fixture(scope="session")
def axe_source() -> str:
    """The vendored axe-core source, after checking it against AXE_SHA256."""
    data = _AXE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == AXE_SHA256, "axe.min.js does not match AXE_SHA256"
    return data.decode("utf-8")


def run_axe(page: Page, axe_source: str) -> list[dict]:  # type: ignore[type-arg]
    """Inject axe-core and return critical and serious violations.

    Serious includes color-contrast and link-in-text-block. It used to be a
    warning only, and every contrast failure on the site shipped green.
    """
    # Inject axe via page.evaluate (CDP Runtime.evaluate), NOT add_script_tag:
    # a <script> element is subject to the page's strict CSP (no 'unsafe-inline'),
    # whereas evaluate runs through the debugger protocol and is CSP-exempt.
    # Wrap in an arrow body so the minified UMD runs regardless of whether its
    # source is an expression or a series of statements.
    page.evaluate("() => { " + axe_source + "\n; }")
    violations: list[dict] = page.evaluate(  # type: ignore[type-arg]
        """
        async () => {
            const results = await axe.run();
            return results.violations.filter(v => ['critical', 'serious'].includes(v.impact));
        }
    """
    )
    return violations


def run_axe_warnings(page: Page, axe_source: str) -> list[dict]:  # type: ignore[type-arg]
    """Return serious (non-critical) axe violations for informational reporting."""
    violations: list[dict] = page.evaluate(  # type: ignore[type-arg]
        """
        async () => {
            const results = await axe.run();
            return results.violations.filter(v => v.impact === 'serious');
        }
    """
    )
    return violations
