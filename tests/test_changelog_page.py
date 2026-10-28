"""/en/changelog/ is rendered at build time from CHANGELOG.md of the latest app release by
scripts/render_changelog.py (scripts/build_site.py calls it). These guards keep the built page
the render of its source, keep the page free of links to anywhere but GitHub and the site's own
domain, and pin the renderer's own escaping and list-nesting behaviour against a small fixture.
The headings-versus-link-definitions check stays with CHANGELOG.md in openwhistle/OpenWhistle."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest
import release_source

from tests.built_site import built

ROOT = Path(__file__).parents[1]


def _page() -> Path:
    return built() / "en/changelog/index.html"


def _load_renderer() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "render_changelog", ROOT / "scripts" / "render_changelog.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDER_CHANGELOG = _load_renderer()


def test_the_built_page_is_the_changelog() -> None:
    versions, link_defs = RENDER_CHANGELOG.parse(release_source.read("CHANGELOG.md"))
    content = RENDER_CHANGELOG.render_content(versions, link_defs, tag=release_source.tag())
    page = _page().read_text(encoding="utf-8")
    assert content in page
    # Its source is the release it renders; main also holds changes not released yet.
    source = f"https://github.com/openwhistle/OpenWhistle/blob/{release_source.tag()}/CHANGELOG.md"
    assert source in page and "blob/main/CHANGELOG.md" not in page


def test_the_older_page_holds_the_rest_and_no_release_is_on_both() -> None:
    versions, link_defs = RENDER_CHANGELOG.parse(release_source.read("CHANGELOG.md"))
    older = RENDER_CHANGELOG.render_content(
        versions, link_defs, tag=release_source.tag(), older=True
    )
    assert older in (built() / "en/changelog/older/index.html").read_text(encoding="utf-8")
    ids = lambda page: set(re.findall(r'<section class="docs-section" id="([^"]+)"', page))  # noqa: E731
    current = ids(RENDER_CHANGELOG.render_content(versions, link_defs, tag="v9.9.9"))
    assert current and ids(older) and not current & ids(older)
    # A release's CHANGELOG.md may carry an empty [Unreleased] or none at all.
    assert "unreleased" not in ids(older)
    # Each closed series has a page of its own, so /older/ does not grow with every release.
    archives = {
        major: RENDER_CHANGELOG.render_content(
            versions, link_defs, tag=release_source.tag(), major=major
        )
        for major in RENDER_CHANGELOG.ARCHIVED
    }
    for major, archive in archives.items():
        assert archive in (built() / f"en/changelog/{major}.x/index.html").read_text("utf-8")
        assert ids(archive) and all(i.startswith(f"v{major}-") for i in ids(archive)), major
        assert not ids(archive) & (current | ids(older)), major
    assert "v1-0-0" in ids(archives["1"]) and "v0-1-0" in ids(archives["0"])
    assert not any(i.startswith(("v0-", "v1-")) for i in ids(older))
    # Unreleased plus the newest NEWEST releases: a count, so a release never breaks the budget.
    assert len(current - {"unreleased"}) <= 5 == RENDER_CHANGELOG.NEWEST


def test_render_content_holds_no_site_chrome() -> None:
    content = RENDER_CHANGELOG.render_content(*RENDER_CHANGELOG.parse(_FIXTURE), tag="v9.9.9")
    assert "<footer" not in content and "site-nav" not in content and "<head" not in content


_HREF_URL_RE = re.compile(r'(?:href|src)="(https?://[^"]+)"')
_ALLOWED_DOMAINS = ("github.com", "openwhistle.net")


def test_page_links_only_to_github_and_its_own_domain() -> None:
    html = _page().read_text(encoding="utf-8")
    offenders = []
    for url in _HREF_URL_RE.findall(html):
        host = re.sub(r"^https?://", "", url).split("/")[0]
        if not any(host == d or host.endswith("." + d) for d in _ALLOWED_DOMAINS):
            offenders.append(url)
    assert not offenders, f"/en/changelog/ links outside github.com/openwhistle.net: {offenders}"


# ── Renderer self-test on a small fixture ──────────────────────────────────

_FIXTURE = """## [9.9.9] — 2026-01-01

A paragraph with a [link](https://example.com/x?a=1&b=2) and `inline code`.

### Added

- A bullet with <script>alert(1)</script> that must come out escaped.
- A bullet with a nested list:
  - first nested item
  - second nested item with `code`
- **Bold** and *italic* together.

[9.9.9]: https://github.com/openwhistle/OpenWhistle/releases/tag/v9.9.9
"""


def test_renderer_escapes_and_nests_correctly_on_a_fixture() -> None:
    versions, link_defs = RENDER_CHANGELOG.parse(_FIXTURE)
    assert [v.name for v in versions] == ["9.9.9"]
    html = RENDER_CHANGELOG.render_content(versions, link_defs, tag="v9.9.9")

    # The literal <script> tag from the source must never appear unescaped.
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    # ...and it must not have been double-escaped either.
    assert "&amp;lt;" not in html

    # A link's URL keeps its query string, its ampersand HTML-escaped.
    assert '<a href="https://example.com/x?a=1&amp;b=2">link</a>' in html

    # Inline code, bold and italic all render as tags, not literal markup.
    assert "<code>inline code</code>" in html
    assert "<strong>Bold</strong>" in html
    assert "<em>italic</em>" in html

    # The nested bullet list is a real <ul> inside the parent <li>, and the
    # parent bullet's own <ul>...</ul> wrapper is not re-escaped.
    assert (
        "<li>A bullet with a nested list:<ul>"
        "<li>first nested item</li>"
        "<li>second nested item with <code>code</code></li>"
        "</ul></li>" in html
    )

    # The heading gets a stable id built from the version number.
    assert 'id="v9-9-9"' in html


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # 0.2.0's line: the italic pass ran over code and paired the two stars.
        (
            "`NOTIFY_EMAIL_*` and `NOTIFY_WEBHOOK_*` variables",
            "<code>NOTIFY_EMAIL_*</code> and <code>NOTIFY_WEBHOOK_*</code> variables",
        ),
        ("`[a](b)` is code", "<code>[a](b)</code> is code"),
        (
            "**`latest` moves** *only* up",
            "<strong><code>latest</code> moves</strong> <em>only</em> up",
        ),
    ],
)
def test_markup_inside_code_stays_code(source: str, expected: str) -> None:
    assert RENDER_CHANGELOG.render_inline(source) == expected


def test_the_older_page_refuses_to_render_empty() -> None:
    few = "\n".join(
        f"## [1.0.{i}] — 2026-01-01\n\n- x\n\n[1.0.{i}]: https://example.test\n" for i in range(5)
    )
    versions, link_defs = RENDER_CHANGELOG.parse(few)
    assert RENDER_CHANGELOG.render_content(versions, link_defs, tag="v9.9.9")
    with pytest.raises(ValueError, match="would be empty"):
        RENDER_CHANGELOG.render_content(versions, link_defs, tag="v9.9.9", older=True)


def test_a_quote_in_a_changelog_url_stays_inside_its_href() -> None:
    """esc() keeps quotes (it escapes text); the URLs went into href="..." through it, so a " in
    CHANGELOG.md ended the attribute and the rest became markup."""
    link = RENDER_CHANGELOG.render_inline('[x](https://a"onmouseover="b)')
    assert link == '<a href="https://a&quot;onmouseover=&quot;b">x</a>'
    version = RENDER_CHANGELOG.Version("9.9.9", "")
    line = RENDER_CHANGELOG.compare_line(version, {"9.9.9": 'https://a/compare/v1"x...v2'})
    assert 'href="https://a/compare/v1&quot;x...v2"' in line
