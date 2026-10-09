"""Layout rules of the site that only a real browser can measure."""

from __future__ import annotations

import pytest
from playwright.sync_api import Browser

from tests.built_site import built, pages

pytestmark = pytest.mark.e2e

# Every page of the built site, as
# the URL it is served at, so a new page is covered the day it is added.
# A build that suddenly finds fewer means the sources moved, not that the
# site shrank.
_DOCS_FILES = {
    "/" + p.relative_to(built()).as_posix().removesuffix("index.html"): p for p in pages()
}
_DOCS_PAGES = sorted(_DOCS_FILES)
_DOCS_PAGE_FLOOR = 9


def test_docs_page_glob_finds_every_page() -> None:
    assert len(_DOCS_PAGES) >= _DOCS_PAGE_FLOOR, _DOCS_PAGES


# `docs_server_url` (module-scoped: builds docs/ and serves the build over HTTP) lives in
# tests/e2e/conftest.py, shared with test_docs_behaviour.py.


# 390 px is a phone; 1024 px is the narrowest desktop width, where the full
# nav row has the least room before it collapses at 1080 px. Both themes: the
# first round of this check only ever ran with the browser's default (light)
# colour scheme, so a dark-only overflow (a token that only widens under
# [data-theme="dark"]) had no test to catch it.
@pytest.mark.parametrize("color_scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [390, 1024])
@pytest.mark.parametrize("docs_page", _DOCS_PAGES)
def test_docs_page_has_no_horizontal_overflow(
    browser: Browser, docs_server_url: str, docs_page: str, width: int, color_scheme: str
) -> None:
    ctx, page = _page(browser, docs_server_url, width, color_scheme=color_scheme)
    page.goto(f"{docs_server_url}{docs_page}")
    page.wait_for_load_state("networkidle")
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    ctx.close()
    assert overflow == 0, (
        f"{docs_page}: {overflow}px horizontal overflow at {width}px ({color_scheme})"
    )


_WIDE_TABLE_PAGES = [u for u in _DOCS_PAGES if "comp-wrap" in _DOCS_FILES[u].read_text()]


@pytest.mark.parametrize("width", [1440, 1920])
@pytest.mark.parametrize("docs_page", _WIDE_TABLE_PAGES)
def test_a_wide_table_is_centred_on_the_text_column(
    browser: Browser, docs_server_url: str, docs_page: str, width: int
) -> None:
    """A table that breaks out of the 70ch prose column stays centred on it.
    Its width was capped at 100ch while its left edge was computed from the
    full window, so on a wide screen it sat flush with the window's left edge."""
    ctx, page = _page(browser, docs_server_url, width)
    page.goto(f"{docs_server_url}{docs_page}")
    offsets = page.evaluate(
        """() => {
            const prose = [...document.querySelectorAll('article p, main p')]
                .find(p => p.getBoundingClientRect().width > 300).getBoundingClientRect();
            const centre = r => (r.left + r.right) / 2;
            return [...document.querySelectorAll('.comp-wrap')]
                .map(w => Math.round(centre(w.getBoundingClientRect()) - centre(prose)));
        }"""
    )
    ctx.close()
    assert offsets, f"{docs_page}: no wide table"
    assert all(abs(o) <= 2 for o in offsets), f"{docs_page}@{width}px: off centre by {offsets}px"


@pytest.mark.parametrize(
    ("width", "sidebar_sticks", "toc_beside"),
    [(1920, True, True), (1280, True, True), (1279, True, False), (769, True, False),
     (768, False, False), (390, False, False)],
)  # fmt: skip
def test_the_docs_columns_follow_the_window_width(
    browser: Browser, docs_server_url: str, width: int, sidebar_sticks: bool, toc_beside: bool
) -> None:
    """DESIGN.md: a persistent sidebar on desktop; "On this page" beside the article from
    1280 px, above it below that; on a phone the menu scrolls away with the page."""
    ctx, page = _page(browser, docs_server_url, width)
    page.goto(f"{docs_server_url}/en/docs/admin/")
    page.evaluate("window.scrollTo({top: 2000, behavior: 'instant'})")
    sidebar, toc, article = page.evaluate(
        """['.docs-sidebar', '.docs-toc', '.docs-article'].map(s => {
             const r = document.querySelector(s).getBoundingClientRect();
             return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; })"""
    )
    ctx.close()
    assert (sidebar["bottom"] > 0) == sidebar_sticks, (width, sidebar)
    assert (toc["left"] >= article["right"]) == toc_beside, (width, toc, article)
    if toc_beside:  # it sticks beside the article, not only at its top
        assert 0 < toc["top"] < 900, (width, toc)
    else:
        assert toc["bottom"] <= article["top"], (width, toc, article)


@pytest.mark.parametrize("url", ["/en/docs/ldap/", "/en/changelog/"])
def test_the_sidebar_and_footer_line_up_with_the_nav(
    browser: Browser, docs_server_url: str, url: str
) -> None:
    """One 1200 px frame site-wide: the sidebar's link text and the footer start on the nav's
    content edge (a 1440 px docs frame put the sidebar 155 px left of the nav logo)."""
    ctx, page = _page(browser, docs_server_url, 1920)
    page.goto(f"{docs_server_url}{url}")
    nav, link, footer = page.evaluate(
        """() => { const inner = s => { const e = document.querySelector(s);
                     return e.getBoundingClientRect().left
                       + parseFloat(getComputedStyle(e).paddingLeft); };
                   const text = document.createRange();
                   text.selectNodeContents(document.querySelector('.sidebar-links a'));
                   return [inner('.nav-inner'), text.getBoundingClientRect().left,
                           inner('.footer-inner')]; }"""
    )
    ctx.close()
    # ±1 px: the old sidebar padding put the text exactly 2 px off, and ±2 let that pass.
    assert abs(link - nav) <= 1 and abs(footer - nav) <= 1, (url, nav, link, footer)


def test_on_a_phone_the_article_starts_under_the_menu_links(
    browser: Browser, docs_server_url: str
) -> None:
    """Below 769 px the menu sits above the article: the open menu's link text and the
    article's text share one left edge (they were 32 and 20 px)."""
    ctx, page = _page(browser, docs_server_url, 390)
    page.goto(f"{docs_server_url}/en/docs/ldap/")
    page.click(".docs-menu > summary")
    link, article = page.evaluate(
        """() => ['.sidebar-links a', '.docs-article p'].map(s => {
             const text = document.createRange();
             text.selectNodeContents(document.querySelector(s));
             return text.getClientRects()[0].left; })"""
    )
    ctx.close()
    assert abs(link - article) <= 1, (link, article)


def _page(browser: Browser, base_url: str, width: int, color_scheme: str = "light"):  # type: ignore[no-untyped-def]
    # The docs pages' own inline script falls back to `prefers-color-scheme`
    # when no `ow-theme` was ever saved in this (fresh) context's localStorage,
    # so setting the context's colour scheme is enough to render dark mode —
    # no cookie or script injection needed.
    ctx = browser.new_context(
        viewport={"width": width, "height": 900}, base_url=base_url, color_scheme=color_scheme
    )
    return ctx, ctx.new_page()
