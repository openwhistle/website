"""Numbers the marketing pages state about the release, read from the release itself.

The comparison pages said 4 interface languages after 2.2.0 added Spanish (app/i18n.py has 5),
one of them two rows below its own "5: German, English, ...", and named 2.1.0 the current
release: nothing compared them with the release.
"""

import re
from pathlib import Path

import release_source
import yaml

from tests.built_site import page, pages

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
