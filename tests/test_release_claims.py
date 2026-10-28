"""Numbers the marketing pages state about the release, read from the release itself.

The comparison pages said 4 interface languages after 2.2.0 added Spanish (app/i18n.py has 5),
one of them two rows below its own "5: German, English, ...", and named 2.1.0 the current
release: nothing compared them with the release.
"""

import html
import json
import re
from pathlib import Path

import release_source
import yaml

from tests.built_site import built, page, pages

ROOT = Path(__file__).parents[1]
BLOG = (
    "/en/blog/whistleblowing-software-comparison/",
    "/de/blog/whistleblower-software-vergleich/",
)


def _languages() -> int:
    return len(release_source.constant("app/i18n.py", "_SUPPORTED"))


def test_the_compare_page_counts_the_releases_languages() -> None:
    row = re.search(r"Interface languages</th>\s*<td>(\d+)</td>", page("/en/compare/"))
    assert row and int(row.group(1)) == _languages(), row and row.group(0)


def _rows(url: str) -> list[str]:
    return [re.sub(r"\s+", " ", r) for r in re.findall(r"<tr>(.*?)</tr>", page(url), re.S)]


def _ow(row: str) -> str:
    """The OpenWhistle cell of a row: the col-ow column, or the product table's last cell."""
    cell = re.search(r'class="col-ow"[^>]*>([^<]*)', row) or re.search(r">([^<]*)</td> $", row)
    assert cell, row
    return cell.group(1)


def test_the_comparison_posts_count_the_releases_languages() -> None:
    for url in BLOG:
        rows = _rows(url)
        cells = [_ow(r) for r in rows if re.match(r" ?<td>(?:Languages|Sprachen)</td>", r)]
        cells += [_ow(r) for r in rows if "<strong>OpenWhistle</strong>" in r]
        counts = [re.match(r"\d+", c) for c in cells]
        assert len(cells) == 3 and all(c and int(c.group()) == _languages() for c in counts), (
            url,
            cells,
        )


def test_the_comparison_posts_name_the_current_release() -> None:
    for url in BLOG:
        rows = [
            r for r in _rows(url) if re.match(r" ?<td>(?:Current release|Aktuelles Release)", r)
        ]
        assert len(rows) == 1 and _ow(rows[0]).startswith(f"{release_source.app_version()},"), (
            url,
            rows,
        )


def test_no_page_says_the_acknowledgement_starts_the_feedback_deadline() -> None:
    """Every report has its feedback deadline from the day it arrives (app/services/report.py,
    deadlines.feedback_due); an acknowledgement can only bring it forward."""
    starts = re.compile(r"start(?:s|et) (?:the|die) [\w -]{0,20}(?:feedback|Rückmelde)", re.I)
    wrong = [str(p) for p in pages() if starts.search(p.read_text(encoding="utf-8"))]
    assert not wrong, wrong


def test_the_admin_guide_names_the_word_search_budget() -> None:
    """The word search reads only the newest CONTENT_SEARCH_LIMIT reports; the guide said it
    searched every report you may see."""
    limit = release_source.constant("app/services/report.py", "CONTENT_SEARCH_LIMIT")
    assert f"the {limit:,} newest reports" in page("/en/docs/admin/")


def test_the_logo_setting_names_the_image_policy_that_limits_it() -> None:
    """The app's CSP decides which logo URLs load at all; the setting said "URL to a logo"."""
    img_src = re.search(r'"(img-src [^;"]*);', release_source.read("app/middleware.py"))
    assert img_src, "app/middleware.py has no img-src directive"
    config = yaml.safe_load((ROOT / "docs/_data/config.yml").read_text(encoding="utf-8"))
    logo = next(s for g in config["groups"] for s in g["settings"] if s["name"] == "BRAND_LOGO_URL")
    assert f"<code>{img_src.group(1)}</code>" in logo["description"], img_src.group(1)


def test_the_roadmap_plans_nothing_its_anonymity_rules_forbid() -> None:
    """Planned webhooks carried case number and timestamp, the planned IP allowlist read the
    client address in the app: both against what the docs promise (counts, never case numbers;
    no handler can read the address)."""
    roadmap = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", page("/en/roadmap/")))
    payload = re.search(r"Payload: ([^.]*\.[^.]*\.)", roadmap)
    assert payload and "No case number, no time" in payload.group(1), payload
    assert "TRUSTED_PROXY_DEPTH" not in roadmap
    assert "never in the app" in roadmap


def test_every_python_version_the_site_names_is_the_releases() -> None:
    """The landing pages said Python 3.14 after the release moved to 3.15 (requires-python)."""
    pyproject = release_source.read("pyproject.toml")
    wanted = re.search(r'^requires-python = ">=(3\.\d+)"$', pyproject, re.M)
    assert wanted, "requires-python not found in the release's pyproject.toml"
    named = {
        path.relative_to(built()).as_posix(): set(re.findall(r"Python (3\.\d+)", path.read_text()))
        for path in pages()
        # the changelog pages: past releases, as the app's CHANGELOG.md wrote them
        if "/changelog/" not in path.as_posix()
    }
    named = {rel: versions for rel, versions in named.items() if versions}
    assert {"en/index.html", "de/index.html"} <= named.keys(), named
    assert all(versions == {wanted[1]} for versions in named.values()), named


def test_a_health_answer_the_site_shows_has_the_releases_fields() -> None:
    """The set-up guides showed "version":"2.1.0" in /health's answer; the release dropped the
    version from it (anyone can call /health) and the pages never followed."""
    reports = release_source.read("app/api/reports.py")
    body = re.search(r"\n    body = \{\n(.*?)\n    \}", reports, re.S)
    assert body, "the /health body is no longer a dict literal in app/api/reports.py"
    fields = set(re.findall(r'^\s+"(\w+)":', body[1], re.M))
    answer = re.compile(r'^# (\{"status":.*\})(?:<|$)', re.M)
    texts = [html.unescape(path.read_text()) for path in pages()]
    shown = [json.loads(found) for text in texts for found in answer.findall(text)]
    assert shown, "no /health answer found on the site — the check reaches nothing"
    assert all(answer.keys() == fields for answer in shown), (fields, shown)


def test_the_security_pages_name_the_releases_image_scanner() -> None:
    """They named Trivy as the image scan after the release made grype the gate (Trivy only
    looks for secrets there)."""
    workflow = release_source.read(".github/workflows/security.yml")
    gates = set(re.findall(r"anchore/(grype)[:@].*?--fail-on", workflow, re.S))
    assert gates == {"grype"}, gates
    phrases = {
        "/en/security/": "on the container image",
        "/de/sicherheit/": "auf das Container-Image",
    }
    for url, phrase in phrases.items():
        named = re.findall(rf"(\w[\w-]*) {re.escape(phrase)}", page(url))
        assert named == ["grype"], (url, named)
