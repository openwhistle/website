"""The site's stylesheets: which exist, who owns the tokens, and what every page links."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.built_site import built, page, pages, stylesheets
from tests.diagram_tools import renderer

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "docs" / "assets" / "css"
ALWAYS = ["tokens.css", "fonts.css", "base.css"]
_DEFINITION = re.compile(r"(?<![\w-])(--[\w-]+)\s*:")


def _sheets(html: str) -> list[str]:
    # fonts-italic.css rides along on the pages that draw italic mono (build_site.py).
    return [p.name for p in stylesheets(html) if p.name != "fonts-italic.css"]


def test_every_page_links_tokens_fonts_and_base_first() -> None:
    for path in pages():
        html = path.read_text(encoding="utf-8")
        assert _sheets(html)[:3] == ALWAYS, path.relative_to(built())


def test_only_tokens_css_defines_custom_properties() -> None:
    offenders = {
        sheet.name: sorted(set(_DEFINITION.findall(sheet.read_text(encoding="utf-8"))))
        for sheet in CSS.glob("*.css")
        if sheet.name != "tokens.css" and _DEFINITION.search(sheet.read_text(encoding="utf-8"))
    }
    assert not offenders, f"custom properties outside tokens.css: {offenders}"


def test_tokens_css_has_a_light_and_a_dark_block_with_the_same_colour_names() -> None:
    text = (CSS / "tokens.css").read_text(encoding="utf-8")
    light = re.search(r":root\s*\{([^}]*)\}", text)
    dark = re.search(r'\[data-theme="dark"\]\s*\{([^}]*)\}', text)
    assert light and dark
    dark_names = set(_DEFINITION.findall(dark.group(1)))
    colour_names = {
        n
        for n, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", light.group(1))
        if re.match(r"#|rgba?\(|color-mix", v.strip())
    }
    assert colour_names == dark_names, colour_names ^ dark_names


def test_tokens_css_names_the_three_font_families() -> None:
    light = re.search(r":root\s*\{([^}]*)\}", (CSS / "tokens.css").read_text(encoding="utf-8"))
    assert light
    fonts = dict(re.findall(r"(--font-[\w-]+)\s*:\s*([^;]+);", light.group(1)))
    assert fonts == {
        "--font-display": "'Sora', system-ui, sans-serif",
        "--font-body": "'Sora', system-ui, sans-serif",
        "--font-mono": "'JetBrains Mono', ui-monospace, monospace",
    }


def test_no_stylesheet_uses_an_undefined_token() -> None:
    defined = set(_DEFINITION.findall((CSS / "tokens.css").read_text(encoding="utf-8")))
    used = {
        (sheet.name, name)
        for sheet in CSS.glob("*.css")
        for name in re.findall(r"var\((--[\w-]+)", sheet.read_text(encoding="utf-8"))
    }
    missing = sorted((s, n) for s, n in used if n not in defined)
    assert not missing, missing


def test_the_retired_token_names_are_gone() -> None:
    retired = (
        "--bg-base", "--bg-surface", "--bg-raised", "--bg-overlay", "--nav-bg", "--footer-bg",
        "--text-primary", "--text-secondary", "--text-muted", "--border-subtle", "--border-default",
        "--border-strong", "--code-bg", "--code-text", "--sidebar-bg", "--red-alert",
    )  # fmt: skip
    for sheet in CSS.glob("*.css"):
        text = sheet.read_text(encoding="utf-8")
        found = [n for n in retired if re.search(re.escape(n) + r"(?![\w-])", text)]
        assert not found, (sheet.name, found)


def test_the_landing_pages_and_posts_share_one_token_sheet() -> None:
    for url in ("/en/", "/de/", "/en/docs/", "/en/changelog/"):
        assert "tokens.css" in _sheets(page(url)), url


PAGE_TYPES = {"home.css", "docs.css", "post.css", "page.css"}


def test_the_site_has_exactly_the_planned_sheets() -> None:
    assert {p.name for p in CSS.glob("*.css")} == set(ALWAYS) | PAGE_TYPES | {"fonts-italic.css"}


# What a page links after the three shared sheets: one page type, or the text pages' docs layout
# plus their extras.
PAGE_SHEETS = (["home.css"], ["docs.css"], ["post.css"], ["docs.css", "page.css"])


def test_every_page_links_its_page_type_sheets() -> None:
    for path in pages():
        sheets = _sheets(path.read_text(encoding="utf-8"))
        assert sheets[3:] in PAGE_SHEETS, (path.relative_to(built()), sheets)


def _scheme_rules(text: str) -> dict[str, str]:
    out = {}
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        if m := re.search(r"color-scheme\s*:\s*([^;]+);", body):
            out[" ".join(selector.split())] = m.group(1).strip()
    return out


def test_each_theme_declares_its_own_color_scheme() -> None:
    """Chrome's Auto Dark Mode recolours a page that does not declare dark support; `light` alone
    does not opt out, `only light` does (https://developer.chrome.com/blog/auto-dark-theme)."""
    want = {'[data-theme="light"]': "only light", '[data-theme="dark"]': "dark"}
    assert _scheme_rules((CSS / "base.css").read_text(encoding="utf-8")) == want


def test_no_template_declares_a_color_scheme() -> None:
    """Only the two theme rules may; an inline `<style>` or include would override them."""
    decl = re.compile(r"(?<![\w-])color-scheme\s*:")
    files = [
        f for d in ("docs/_includes", "docs/_layouts") for f in (ROOT / d).rglob("*") if f.is_file()
    ]
    assert files
    assert [str(f) for f in files if decl.search(f.read_text(encoding="utf-8"))] == []


def _rules(text: str, media: str = "") -> dict[tuple[str, str], list[str]]:
    """(media, selector) -> sorted declarations, for flat sheets with @media one level deep."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out: dict[tuple[str, str], list[str]] = {}
    i = 0
    while (brace := text.find("{", i)) != -1:
        head = " ".join(text[i:brace].split())
        depth, end = 1, brace + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        body = text[brace + 1 : end - 1]
        if head.startswith("@media"):
            out.update(_rules(body, head))
        elif not head.startswith("@"):
            decls = sorted(" ".join(d.split()) for d in body.split(";") if d.strip())
            out[(media, head)] = decls
        i = end
    return out


def test_page_css_redefines_no_docs_selector() -> None:
    """Text pages link docs.css and page.css: page.css adds to the docs layout, never copies it."""
    docs = _rules((CSS / "docs.css").read_text(encoding="utf-8"))
    page_ = _rules((CSS / "page.css").read_text(encoding="utf-8"))
    assert len(docs) > 30 and page_
    assert not sorted(docs.keys() & page_.keys())


# The same selector, styled differently in two page-type sheets, on purpose. Each entry names why.
PAGE_TYPE_DIFFERENCES = {
    # Home figures sit in grid rows that space them; docs figures sit in running text.
    ("home.css", "docs.css", ("", ".diagram, .doc-shot")),
    # docs.css: a safety net for any bare <pre>; post.css: the posts' code block itself.
    ("docs.css", "post.css", ("", "pre")),
    # One class name, two components: the blog index card (page.css), the post header (post.css).
    ("post.css", "page.css", ("", ".article-meta")),
    ("post.css", "page.css", ("", ".article-tag")),
    ("post.css", "page.css", ("", ".article-title")),
}


def test_no_selector_drifts_between_two_page_type_sheets() -> None:
    names = ["home.css", "docs.css", "post.css", "page.css"]
    sheets = {n: _rules((CSS / n).read_text(encoding="utf-8")) for n in names}
    drifted = sorted(
        (a, b, key)
        for i, a in enumerate(names)
        for b in names[i + 1 :]
        for key in sheets[a].keys() & sheets[b].keys()
        if sheets[a][key] != sheets[b][key] and (a, b, key) not in PAGE_TYPE_DIFFERENCES
    )
    assert not drifted, drifted
    stale = [
        (a, b, k)
        for a, b, k in PAGE_TYPE_DIFFERENCES
        if k not in sheets[a].keys() & sheets[b].keys()
    ]
    assert not stale, stale


_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_COLOUR_FN = re.compile(r"(?<![\w-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)
_WORD = re.compile(r"(?<![\w-])[a-zA-Z]+(?![\w-])")
# CSS Color 4 named colours. transparent and currentColor are not a colour of their own.
NAMED_COLOURS = frozenset(
    """aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
    blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson
    cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
    darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray
    darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick
    floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey
    honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon
    lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
    lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow
    lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple
    mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue
    mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
    palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
    powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen
    seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal
    thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen""".split()
)
# Illustrations of other software's chrome, not brand colour: the macOS window buttons
# of the home page's terminal mockup. Allowed in home.css only.
FOREIGN_COLOURS = {"#ff5f57", "#febc2e", "#28c840"}


def colour_literals(value: str) -> set[str]:
    """Every colour a CSS value writes itself: hex, a colour function, a named colour."""
    found = {c.lower() for c in _HEX.findall(value)}
    found |= {m.group(0).lower() for m in _COLOUR_FN.finditer(value)}
    return found | ({w.lower() for w in _WORD.findall(value)} & NAMED_COLOURS)


@pytest.mark.parametrize(
    "value",
    ["#fff", "rgb(0 0 0)", "hsl(0 0% 100%)", "oklch(70% 0.1 160)", "lab(50 0 0)", "white",
     "color-mix(in srgb, var(--accent) 50%, white)", "1px solid Black", "color(srgb 1 1 1)"],
)  # fmt: skip
def test_the_colour_scan_sees_every_kind_of_literal(value: str) -> None:
    assert colour_literals(value), value


@pytest.mark.parametrize(
    "value",
    ["var(--accent)", "transparent", "currentColor", "nowrap", "1px solid var(--hairline)",
     "color-mix(in srgb, var(--accent) 8%, transparent)", "'Sora', system-ui, sans-serif"],
)  # fmt: skip
def test_the_colour_scan_passes_tokens_and_keywords(value: str) -> None:
    assert not colour_literals(value), value


def _declarations(css: str) -> list[tuple[str, str]]:
    return re.findall(r"([\w-]+)\s*:\s*([^;{}]+)[;}]", re.sub(r"/\*.*?\*/", "", css, flags=re.S))


def _block(text: str, opener: str) -> dict[str, str]:
    """Custom properties of every rule whose whole selector is `opener`; later rules win."""
    rule = r"(?:\A|(?<=\}))(?:\s|/\*.*?\*/)*" + re.escape(opener) + r"\s*\{([^}]*)\}"
    bodies = re.findall(rule, text, flags=re.S)
    assert bodies, opener
    return {
        k: v.strip() for body in bodies for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body)
    }


def test_every_colour_value_in_tokens_css_is_a_design_md_colour() -> None:
    """A token named after a DESIGN.md key carries that key's value; any other colour literal is a
    DESIGN.md colour, and everything else is derived from a token (color-mix)."""
    palette = renderer().palette()
    text = (CSS / "tokens.css").read_text(encoding="utf-8")
    for theme, opener in (("light", ":root"), ("dark", '[data-theme="dark"]')):
        for name, value in _block(text, opener).items():
            if (key := name[2:]) in palette[theme]:
                assert value.lower() == palette[theme][key], (theme, name, value)
                continue
            for literal in colour_literals(value):
                assert literal in set(palette[theme].values()), (
                    theme,
                    name,
                    literal,
                    "derive with color-mix(in srgb, var(--x) N%, transparent)",
                )


def _rounded() -> dict[str, str]:
    """DESIGN.md's `rounded` scale from its front matter."""
    front = (ROOT / "DESIGN.md").read_text(encoding="utf-8").split("---", 2)[1]
    block = re.search(r"^rounded:\n((?:  .*\n)+)", front, re.M)
    assert block
    return dict(re.findall(r'^  ([\w-]+):\s*"([^"]+)"', block.group(1), re.M))


def test_tokens_css_radii_are_design_md_rounded() -> None:
    root = _block((CSS / "tokens.css").read_text(encoding="utf-8"), ":root")
    radii = {k.removeprefix("--radius-"): v for k, v in root.items() if k.startswith("--radius-")}
    assert radii == {k: v for k, v in _rounded().items() if k != "none"}


def test_page_sheets_round_corners_only_with_the_radius_tokens() -> None:
    """DESIGN.md "Shapes": one scale for site and app; a corner is a token or square."""
    token = re.compile(r"var\(--radius-(?:sm|md|lg|full)\)|0")
    for sheet in CSS.glob("*.css"):
        for prop, value in _declarations(sheet.read_text(encoding="utf-8")):
            if prop.startswith("border") and prop.endswith("radius"):
                stray = [v for v in value.split() if not token.fullmatch(v)]
                assert not stray, (sheet.name, prop, value)


def test_no_page_sheet_writes_a_colour_literal() -> None:
    for sheet in CSS.glob("*.css"):
        if sheet.name == "tokens.css":
            continue
        values = (v for _, v in _declarations(sheet.read_text(encoding="utf-8")))
        stray = set().union(*map(colour_literals, values))
        if sheet.name == "home.css":
            stray -= FOREIGN_COLOURS
        assert not stray, (sheet.name, sorted(stray))


_PAINT = re.compile(
    r"""(?<![\w-])(?:fill|stroke|stop-color|color|style)\s*=\s*(["'])(.*?)\1""", re.S
)


def test_no_page_paints_with_a_colour_literal() -> None:
    """Inline SVG takes currentColor and a sheet colours it: a literal skips the theme."""
    offenders = {}
    for path in pages():
        text = path.read_text(encoding="utf-8")
        found = set().union(*(colour_literals(v) for _, v in _PAINT.findall(text)))
        if found:
            offenders[str(path.relative_to(built()))] = sorted(found)
    assert not offenders, offenders


def test_headings_balance_their_lines() -> None:
    text = (CSS / "base.css").read_text(encoding="utf-8")
    assert re.search(r"h1,\s*h2,\s*h3[^{]*\{[^}]*text-wrap:\s*balance", text)


def test_nothing_transitions_all() -> None:
    for sheet in CSS.glob("*.css"):
        css = sheet.read_text(encoding="utf-8")
        assert not re.search(r"transition(-property)?\s*:\s*all\b", css), sheet.name


# A rule's selector starts after the previous rule's `}` or after an `@media {`.
RULE = r"(?:\A|(?<=[{}]))\s*([^{}@]+?)\s*\{([^{}]*)\}"
# A 1px ring anywhere in a box-shadow list, inset or not.
RING = r"box-shadow:[^;]*?(?<![\w.-])0 0 0 1px"


def _rule_selectors(text: str) -> list[tuple[set[str], str]]:
    """Every top-level rule as (its comma-separated selectors, its body)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return [({s.strip() for s in head.split(",")}, body) for head, body in re.findall(RULE, text)]


def test_figures_are_tabular() -> None:
    base = (CSS / "base.css").read_text(encoding="utf-8")
    assert re.search(r"table[^{]*\{[^}]*tabular-nums", base)


_FORCED = "@media (forced-colors: active) {"


def _forced_blocks(text: str) -> list[tuple[int, int]]:
    """(start, end) of every forced-colours block, matched by brace depth: an indented block
    once ended at the next unindented `}` and hid every rule up to it from these checks."""
    blocks, start = [], text.find(_FORCED)
    while start != -1:
        depth, i = 0, start + len(_FORCED) - 1
        while True:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
            if not depth:
                break
        blocks.append((start, i))
        start = text.find(_FORCED, i)
    return blocks


def _stripped(path: Path) -> str:
    """The sheet without its forced-colours blocks, which draw real borders on purpose."""
    text = path.read_text("utf-8")
    for start, end in reversed(_forced_blocks(text)):
        text = text[:start] + text[end:]
    return text


def test_a_forced_colours_block_ends_at_its_own_brace() -> None:
    css = "a {}\n  @media (forced-colors: active) {\n    .x { border: 1px solid; }\n  }\n  .y {}\n}"
    assert _forced_blocks(css) == [(7, css.index(".y") - 3)]


def test_no_site_component_draws_a_decorative_border() -> None:
    """DESIGN.md "Rules": a decorative edge is a box-shadow ring; only structural borders
    (row separators, accent bars: border-top/bottom/left) stay."""
    for sheet in CSS.glob("*.css"):
        found = re.search(r"(?<![-\w])border(-width)?:\s*[\d.]+px", _stripped(sheet))
        assert not found, (sheet.name, found and found.group(0))


def _forced_colours(path: Path) -> str:
    text = path.read_text("utf-8")
    return "\n".join(text[start + len(_FORCED) : end - 1] for start, end in _forced_blocks(text))


def _listed(block: str, selector: str) -> bool:
    plain = selector.removeprefix('[data-theme="dark"] ')
    return plain in {s.strip() for s in re.split(r"[,{}]", block)}


def test_every_ringed_site_component_has_a_forced_colours_border() -> None:
    block = _forced_colours(CSS / "base.css")
    missing: set[str] = set()
    for sheet in CSS.glob("*.css"):
        text = _stripped(sheet)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for head, body in re.findall(RULE, text):
            if not re.search(RING, body):
                continue
            for s in (x.strip() for x in head.split(",")):
                if ":" not in s.removeprefix('[data-theme="dark"] ') and not _listed(block, s):
                    missing.add(f"{sheet.name}: {s}")
    assert not missing, sorted(missing)


def test_a_hover_that_changes_the_ring_transitions_it() -> None:
    """A transition list without box-shadow makes the ring snap while the fill fades."""
    for sheet in CSS.glob("*.css"):
        rules = _rule_selectors(_stripped(sheet))
        for sels, body in rules:
            for hover in (s for s in sels if s.endswith(":hover") and "box-shadow" in body):
                base = hover.removesuffix(":hover")
                lists = [
                    m.group(1)
                    for bsels, bbody in rules
                    if base in bsels
                    for m in [re.search(r"transition(?:-property)?:\s*([^;]+);", bbody)]
                    if m
                ]
                assert all("box-shadow" in x for x in lists), (sheet.name, base, lists)


def test_a_transition_property_list_names_each_property_once() -> None:
    for sheet in CSS.glob("*.css"):
        for names in re.findall(r"transition-property:\s*([^;]+);", sheet.read_text("utf-8")):
            parts = [n.strip() for n in names.split(",")]
            assert len(parts) == len(set(parts)), (sheet.name, names)


# Every code sample has one look: a framed, labelled .code-block. A post's <pre> is framed by
# post.css (.article-body pre) and the home terminal by .terminal-window; nothing else may be bare.
PRE_HOMES = ("code-block", "terminal-window", "article-body")
_VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "col", "area", "base"}


class _PreFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[set[str]] = []
        self.bare = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID:
            return
        classes = set(dict(attrs).get("class", "").split())
        if tag == "pre" and not any(c in PRE_HOMES for s in self.stack for c in s):
            self.bare += 1
        self.stack.append(classes)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID and self.stack:
            self.stack.pop()


def test_every_class_a_sheet_styles_is_on_some_page() -> None:
    """A rule for a class no page or script uses is dead weight a reader still has to read."""
    text = " ".join(p.read_text(encoding="utf-8") for p in pages())
    text += " ".join(p.read_text(encoding="utf-8") for p in (ROOT / "docs/assets/js").glob("*.js"))
    used = {c for m in re.findall(r'class="([^"]*)"', text) for c in m.split()}
    used |= set(re.findall(r"classList\.\w+\('([\w-]+)'", text))
    dead = {}
    for sheet in CSS.glob("*.css"):
        heads = re.findall(
            r"([^{}]+)\{", re.sub(r"/\*.*?\*/", "", sheet.read_text("utf-8"), flags=re.S)
        )
        styled = set(re.findall(r"\.([a-zA-Z][\w-]*)", " ".join(h for h in heads if "@" not in h)))
        if unused := sorted(styled - used):
            dead[sheet.name] = unused
    assert not dead, dead


def test_every_pre_sits_in_a_framed_code_component() -> None:
    bare = {}
    for path in pages():
        finder = _PreFinder()
        finder.feed(path.read_text(encoding="utf-8"))
        if finder.bare:
            bare[str(path.relative_to(built()))] = finder.bare
    assert not bare, bare
