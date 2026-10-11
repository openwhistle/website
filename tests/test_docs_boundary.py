"""Two documentations, one boundary: docs/ is published for whoever runs
OpenWhistle, docs-tech/ is for whoever maintains the repository and never is."""

import hashlib
import re
from pathlib import Path

import yaml
from build_site import split_front_matter

from tests.built_site import built, page, pages

ROOT = Path(__file__).parents[1]


def test_the_technical_docs_are_not_published() -> None:
    tech = ROOT / "docs-tech"
    assert tech.is_dir() and any(tech.iterdir()), "docs-tech/ is missing or empty"

    for name in ("docs-tech", "technical", "internal"):
        assert not (ROOT / "docs" / name).exists(), (
            f"docs/{name} exists — everything under docs/ is published in the website image"
        )


_DOCS_TECH_HREF = re.compile(r'(?:href|src)=["\']([^"\']*docs-tech/[^"\']*)["\']')


def test_no_published_page_links_docs_tech() -> None:
    """docs-tech/ is never uploaded, so a relative link 404s; and a GitHub URL
    sends an operator to a maintainer page. Naming a docs-tech/ file in
    running text is fine, a link is not."""
    offenders = [
        f"{p.relative_to(built())}: {m.group(1)}"
        for p in pages()
        for m in _DOCS_TECH_HREF.finditer(p.read_text())
    ]
    assert not offenders, f"published page(s) link docs-tech/: {offenders}"


def test_the_public_roadmap_holds_no_test_chores() -> None:
    """Test infrastructure changes nothing a user sees; it is planned in
    docs-tech/test-infrastructure.md of openwhistle/OpenWhistle, not on the published roadmap."""
    roadmap = page("/en/roadmap/")
    assert not re.search(r"\btests/|\btest_\w+", roadmap)


def test_the_image_publishes_the_built_site_and_nothing_else() -> None:
    dockerfile = (ROOT / "website/Dockerfile").read_text()
    build = next(line for line in dockerfile.splitlines() if "build_site.py" in line)
    # Its other input is the app release (OW_APP_SOURCE, scripts/release_source.py), never pages.
    assert "--src" not in build, "the build must read docs/ and nothing else"
    assert "COPY --from=site /out/site /usr/share/nginx/html" in dockerfile


def test_the_image_build_checks_out_the_full_history() -> None:
    """Shallow history makes every sitemap lastmod the deploy date, silently."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/website-image.yml").read_text())
    for name, job in workflow["jobs"].items():
        checkout = next(s for s in job["steps"] if "actions/checkout" in s.get("uses", ""))
        assert checkout.get("with", {}).get("fetch-depth") == 0, name


def _from_docs_tech(src: Path, out: Path) -> list[str]:
    """Files of `out` (the build) or pages of `src` (docs/) that are a docs-tech/ file."""
    tech_files = [p for p in (ROOT / "docs-tech").rglob("*") if p.is_file()]
    tech_names = {p.name for p in tech_files if p.suffix == ".md"}
    # An empty file says nothing; any empty built file would collide with it.
    tech_hashes = {
        hashlib.sha256(p.read_bytes()).hexdigest() for p in tech_files if p.stat().st_size
    }
    tech_texts = {p.read_text(encoding="utf-8").strip() for p in tech_files if p.suffix == ".md"}
    leaked = [
        str(p) for p in out.rglob("*") if p.is_file()
        and hashlib.sha256(p.read_bytes()).hexdigest() in tech_hashes
    ]  # fmt: skip
    # The build renders a .md page to HTML, so neither its name nor its bytes reach the output:
    # the source is where a copied docs-tech page shows. It used to be checked on the build
    # only, where no .md exists, and a docs-tech page given front matter was published.
    for md in src.rglob("*.md"):
        _meta, body = split_front_matter(md.relative_to(src), md.read_text(encoding="utf-8"))
        if md.name in tech_names or body.strip() in tech_texts:
            leaked.append(str(md))
    return sorted(leaked)


def test_no_built_file_comes_from_docs_tech() -> None:
    """Neither by name nor by content."""
    leaked = _from_docs_tech(ROOT / "docs", built())
    assert not leaked, leaked


def test_a_docs_tech_page_given_front_matter_is_caught(tmp_path: Path) -> None:
    tech = (ROOT / "docs-tech" / "invariants.md").read_text(encoding="utf-8")
    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "rules.md").write_text(f"---\ntitle: x\n---\n{tech}", encoding="utf-8")
    (tmp_path / "en" / "local-review.md").write_text("---\ntitle: x\n---\nother", encoding="utf-8")
    assert _from_docs_tech(tmp_path, tmp_path / "out") == [
        str(tmp_path / "en" / "local-review.md"),
        str(tmp_path / "en" / "rules.md"),
    ]
