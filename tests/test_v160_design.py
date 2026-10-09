"""v1.6.0 design rules of the site, pinned in the built pages and their stylesheets.

The app's templates and stylesheet: the same rules in openwhistle/OpenWhistle.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

import release_source
from fontTools.ttLib import TTFont

from tests.built_site import builder, built, css_of, page, pages, stylesheets

ROOT = Path(__file__).parents[1]


def test_brand_secondary_colour_is_gone() -> None:
    # The release's config.py names it only to ignore a stale .env entry.
    assert "BRAND_SECONDARY_COLOR" not in release_source.settings()
    for path in (ROOT / "docs/en/docs").rglob("index.html"):
        text = path.read_text().lower().replace("-", "_")
        assert "brand_secondary" not in text, path.relative_to(ROOT).as_posix()


def test_public_site_uses_the_app_token_names() -> None:
    for path in pages():
        html = path.read_text()
        text = html + css_of(html)
        for legacy in ("--gold", "--seal-green", "--font-serif"):
            assert legacy not in text, (path.relative_to(built()).as_posix(), legacy)


_WARNING_PAGES = (
    "/en/docs/demo-mode/",
    "/en/docs/install/",
    "/en/docs/onion/",
    "/en/docs/requirements/",
    "/en/docs/rotate-key/",
    "/de/blog/hinschg-compliance-leitfaden/",
    "/de/blog/interne-meldestelle-einrichten/",
    "/de/blog/whistleblower-software-vergleich/",
    "/de/blog/was-ist-neu-in-2-0/",
)


def test_docs_warn_callouts_do_not_converge_on_the_accent() -> None:
    """Regression guard: folding --gold and --seal-green onto one --accent
    token must not leave a "warning" callout coloured identically to the
    brand accent (or to a "note"/"info" callout). .callout-warn and
    .val-warn must use their own --warning token."""
    for name in _WARNING_PAGES:
        text = css_of(page(name))
        assert "--warning" in text, name
        for selector in (".callout-warn", ".val-warn"):
            for body in re.findall(re.escape(selector) + r"[^{]*\{([^}]*)\}", text):
                assert "var(--accent)" not in body, (name, selector, body)


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")

    def channel(c: str) -> float:
        v = int(c, 16) / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(hex_color[i : i + 2]) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.1 contrast ratio between two hex colours."""
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    la, lb = max(la, lb), min(la, lb)
    return (la + 0.05) / (lb + 0.05)


def test_docs_warning_colour_meets_contrast() -> None:
    """The site's --warning must read against its --canvas at >= 4.5:1 (WCAG AA,
    normal text) in both themes — a warning colour nobody can read is not a fix
    (the former gold light value #c8972e was ~2.5:1 on the blog pages). The
    tokens exist once, in tokens.css, which every warning page links."""
    tokens = (ROOT / "docs" / "assets" / "css" / "tokens.css").read_text(encoding="utf-8")
    for name in _WARNING_PAGES:
        assert "/assets/css/tokens.css" in page(name), name
    light_block = re.search(r":root\s*\{([^}]*)\}", tokens)
    dark_block = re.search(r'\[data-theme="dark"\]\s*\{([^}]*)\}', tokens)
    assert light_block and dark_block
    for theme, block in (("light", light_block), ("dark", dark_block)):
        warning = re.search(r"--warning:\s*(#[0-9a-fA-F]{6})", block.group(1))
        canvas = re.search(r"--canvas:\s*(#[0-9a-fA-F]{6})", block.group(1))
        assert warning and canvas, theme
        ratio = _contrast_ratio(warning.group(1), canvas.group(1))
        assert ratio >= 4.5, (theme, warning.group(1), canvas.group(1), ratio)


def test_every_docs_font_face_url_resolves_to_a_real_file() -> None:
    """Regression guard: docs/blog's four articles and its index declared
    @font-face rules for Spectral/Source Serif 4 that pointed at files which
    did not exist anywhere in the repo (fetched once in commit fc47183, then
    deleted by an unrelated redesign, commit 241e926, that never touched the
    older blog scaffold) -- every browser silently fell back to the declared
    Georgia/serif fallback, so nothing visibly broke, but nothing was
    actually self-hosted either. This scans every @font-face in the CSS of
    every built page (inline and linked) and asserts its url()'s local path
    exists in the built site."""
    url_re = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)")
    font_face_re = re.compile(r"@font-face\s*\{[^}]*\}", re.DOTALL)
    checked = 0
    site = built()
    for path in pages():
        html = path.read_text(encoding="utf-8")
        # Inline CSS resolves against its page, a stylesheet's url() against the sheet.
        inline = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S)
        styles = [(css, path.parent) for css in inline]
        styles += [(sheet.read_text(encoding="utf-8"), sheet.parent) for sheet in stylesheets(html)]
        for text, here in styles:
            for block in font_face_re.findall(text):
                for m in url_re.finditer(block):
                    src = m.group(1)
                    if src.startswith("data:"):
                        # The site inlines its fonts: the face must be a woff2 that decodes.
                        match = re.fullmatch(r"data:font/woff2;base64,([A-Za-z0-9+/=]+)", src)
                        assert match, f"{path.relative_to(site)}: a data: face that is no woff2"
                        font = TTFont(io.BytesIO(base64.b64decode(match.group(1))))
                        assert len(font.getBestCmap()) > 50, f"{src[:40]}: not a text font"
                        checked += 1
                        continue
                    if src.startswith(("http://", "https://")):
                        continue
                    base = site if src.startswith("/") else here
                    resolved = (base / src.lstrip("/")).resolve()
                    assert resolved.is_file(), f"{path.relative_to(site)}: {src} does not exist"
                    checked += 1
    assert checked, "no @font-face url() found in the built site -- test target moved?"


def _unwrap_at_rules(css: str) -> str:
    """Flatten @media { ... } blocks so a flat rule scan also sees the rules
    inside them (font-face/family/weight declarations never live under any
    other at-rule on these pages)."""
    out: list[str] = []
    i, n = 0, len(css)
    while i < n:
        m = re.match(r"@media[^{]*\{", css[i:])
        if m and not css[i:].startswith("@font-face"):
            start = i + m.end()
            depth, j = 1, start
            while j < n and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            out.append(_unwrap_at_rules(css[start : j - 1]))
            i = j
        else:
            out.append(css[i])
            i += 1
    return "".join(out)


def _norm_weight(w: str) -> int | str:
    w = w.strip().lower()
    mapped = {"normal": 400, "bold": 700}
    if w in mapped:
        return mapped[w]
    try:
        return int(w)
    except ValueError:
        return w


def _weight_range(w: str) -> tuple[int, int] | str:
    """A face's `font-weight`: one weight or a variable font's `low high` range."""
    parts = [_norm_weight(p) for p in w.split()]
    if all(isinstance(p, int) for p in parts) and parts:
        return (int(parts[0]), int(parts[-1]))  # type: ignore[arg-type]
    return w.strip()


def _norm_style(s: str) -> str:
    s = s.strip().lower()
    return s if s in ("italic", "oblique") else "normal"


def _resolve_family(famval: str, varmap: dict[str, str]) -> str | None:
    m = re.match(r"var\((--font-[a-zA-Z-]+)\)", famval)
    if m:
        return varmap.get(m.group(1))
    return famval.split(",")[0].strip().strip("'\"")


# A selector whose real font context comes from a nested/descendant
# relationship a flat CSS rule scan can't see (e.g. an inline <em> inside a
# paragraph that itself sets an explicit weight, or a code-comment span
# inside a code block whose ancestor overrides font-family to the mono
# stack) -- keyed by the exact relative page path, since the same class name
# can sit under a different real ancestor on a different page -- keyed by URL.
_DOCS_CSS_ANCESTORS = {
    ".t-comment": ".code-block pre code",  # ancestor sets font-family: var(--font-mono)
}


_ANCESTOR_OVERRIDES: dict[str, dict[str, str]] = {
    "/en/": {
        ".hero-subline em": ".hero-subline",  # inherits its weight (300), not body's default
        ".hero-headline .accent-emphasis": ".hero-headline",  # inherits its weight (700)
        ".t-comment": ".terminal-body",  # ancestor sets font-family: var(--font-mono)
    },
    "/de/": {
        ".hero-subline em": ".hero-subline",
        ".hero-headline .accent-emphasis": ".hero-headline",
        ".t-comment": ".terminal-body",
    },
}


def test_every_docs_page_font_usage_has_a_matching_font_face() -> None:
    """A page that asks for a weight or style its self-hosted family does
    not ship gets a synthesized faux face from the browser. For every
    built page, every (font-family, font-weight, font-style) its CSS
    declares (in the same rule, or inherited from body/an explicit ancestor
    override above) for a family the page self-hosts at all must have a
    matching @font-face -- not just "the url resolves", but "the exact face
    used exists"."""
    font_face_re = re.compile(r"@font-face\s*\{([^}]*)\}", re.DOTALL)
    fam_re = re.compile(r"font-family:\s*['\"]?([^'\";]+)['\"]?")
    weight_re = re.compile(r"font-weight:\s*([^;]+);")
    style_re = re.compile(r"font-style:\s*([^;]+);")
    var_re = re.compile(r"(--font-[a-zA-Z-]+)\s*:\s*([^;]+);")
    rule_re = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)

    checked_pages = 0
    for path in pages():
        rel = "/" + path.relative_to(built()).as_posix().removesuffix("index.html")
        style = css_of(path.read_text(encoding="utf-8"))
        if not style.strip():
            continue
        style = _unwrap_at_rules(style)

        faces: set[tuple[str, tuple[int, int] | str, str]] = set()
        for block in font_face_re.findall(style):
            fam_m = fam_re.search(block)
            if not fam_m:
                continue
            w_m, s_m = weight_re.search(block), style_re.search(block)
            faces.add(
                (
                    fam_m.group(1).strip(),
                    _weight_range(w_m.group(1)) if w_m else (400, 400),
                    _norm_style(s_m.group(1)) if s_m else "normal",
                )
            )
        if not faces:
            continue
        checked_pages += 1
        hosted_families = {f for f, _w, _s in faces}
        varmap = {
            name: val.split(",")[0].strip().strip("'\"") for name, val in var_re.findall(style)
        }
        rest = font_face_re.sub("", style)
        links_docs_css = any(s.name == "docs.css" for s in stylesheets(path.read_text("utf-8")))
        ancestors = _ANCESTOR_OVERRIDES.get(rel) or (_DOCS_CSS_ANCESTORS if links_docs_css else {})

        rules: dict[str, dict[str, object]] = {}
        for sel, decl in rule_re.findall(rest):
            sel_clean = sel.strip().replace("\n", " ")
            fam_m, w_m, s_m = fam_re.search(decl), weight_re.search(decl), style_re.search(decl)
            rules[sel_clean] = {
                "family": _resolve_family(fam_m.group(1).strip(), varmap) if fam_m else None,
                "weight": _norm_weight(w_m.group(1)) if w_m else None,
                "style": _norm_style(s_m.group(1)) if s_m else None,
            }

        def resolve(
            sel: str,
            seen: frozenset[str] = frozenset(),
            rules: dict[str, dict[str, object]] = rules,
            ancestors: dict[str, str] = ancestors,
        ) -> tuple[str | None, int | str, str]:
            r = rules.get(sel, {})
            fam, w, s = r.get("family"), r.get("weight"), r.get("style")
            parent = ancestors.get(sel, "body" if sel != "body" else None)
            if (fam is None or w is None) and parent and parent not in seen:
                pfam, pw, _ps = resolve(parent, seen | {sel}, rules, ancestors)
                fam = fam or pfam
                w = w if w is not None else pw
            return fam, (w if w is not None else 400), (s or "normal")

        for sel, r in rules.items():
            if r["family"] is None and r["weight"] is None and r["style"] is None:
                continue
            fam, w, s = resolve(sel)
            if fam not in hosted_families:
                continue
            if (fam, s) == ("JetBrains Mono", "italic") and not builder().mono_italic_text(
                path.read_text(encoding="utf-8")
            ):
                continue  # the italic face is linked only by the pages that draw it
            if any(
                f == fam and st == s and isinstance(r, tuple) and r[0] <= w <= r[1]
                for f, r, st in faces
                if isinstance(w, int)
            ):
                continue
            raise AssertionError(
                f"{rel}: {sel!r} uses {fam} weight={w} style={s}, "
                f"but no matching @font-face exists (has: {sorted(map(str, faces))})"
            )
    assert checked_pages, "no built page with @font-face declarations found -- test target moved?"
    assert set(_ANCESTOR_OVERRIDES) <= {
        "/" + p.relative_to(built()).as_posix().removesuffix("index.html") for p in pages()
    }, "an _ANCESTOR_OVERRIDES key names no built page"


def test_blog_1_6_release_date_is_2026_09_26() -> None:
    """The article was dated 25 September while the
    actual release is the 26th — every date on the page, the sitemap and the
    JSON-LD must agree with the real release date."""
    text = page("/de/blog/was-ist-neu-in-2-0/")
    assert "25. September 2026" not in text
    assert "2026-09-25" not in text
    assert "26. September 2026" in text
    assert text.count('"2026-09-26"') >= 2  # datePublished, article:published_time

    sitemap = (built() / "sitemap.xml").read_text()
    article_block = re.search(
        r"<loc>https://openwhistle\.net/de/blog/was-ist-neu-in-2-0/</loc>.*?</url>",
        sitemap,
        re.DOTALL,
    )
    assert article_block, "sitemap entry for the 2.0 blog article not found"
    # lastmod comes from git: the release day, or a later edit (the 2.0.1 note).
    lastmod = re.search(r"<lastmod>([0-9-]+)</lastmod>", article_block.group(0))
    assert lastmod and lastmod.group(1) >= "2026-09-26", article_block.group(0)
