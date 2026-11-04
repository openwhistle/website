"""/security.json: what every OpenWhistle installation fetches daily. A feed the app would drop
fails the build; it is never published."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import security_feed

from tests.built_site import builder, built
from tests.conftest import FIXTURE_FEED

FEED = json.loads(FIXTURE_FEED.read_text(encoding="utf-8"))
GITHUB_ADVISORY = {
    "ghsa_id": "GHSA-2c4f-6h8j-9mpq",
    "cve_id": "CVE-2026-0001",
    "summary": "Fixture advisory: never published",
    "severity": "high",
    "html_url": "https://github.com/openwhistle/OpenWhistle/security/advisories/GHSA-2c4f-6h8j-9mpq",
    "description": "not carried",
    "vulnerabilities": [
        {
            "package": {"ecosystem": "other", "name": "openwhistle"},
            "vulnerable_version_range": ">= 1.4.0, < 2.4.2",
            "patched_versions": "2.4.2",
        }
    ],
}
GITHUB_RELEASE = {
    "tag_name": "v2.4.2",
    "html_url": "https://github.com/openwhistle/OpenWhistle/releases/tag/v2.4.2",
    "published_at": "2026-11-01T10:00:00Z",
}


def test_github_data_maps_to_schema_1() -> None:
    assert security_feed.from_github([GITHUB_ADVISORY], GITHUB_RELEASE) == FEED


def test_an_advisory_without_a_cve_or_a_fix_yet_is_still_published() -> None:
    adv = {**GITHUB_ADVISORY, "cve_id": None}
    adv["vulnerabilities"] = [{"vulnerable_version_range": "<= 2.4.2", "patched_versions": None}]
    [entry] = security_feed.from_github([adv], GITHUB_RELEASE)["advisories"]
    assert (entry["cve_ids"], entry["fixed"]) == ([], "")


def _broken(path: str, value: Any) -> dict[str, Any]:
    feed = copy.deepcopy(FEED)
    *parents, last = path.split(".")
    node: Any = feed
    for part in parents:
        node = node[int(part)] if part.isdigit() else node[part]
    node[last] = value
    return feed


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("schema", 2),
        ("latest.version", "latest"),
        ("latest.url", "http://example.org/"),
        ("advisories.0.id", "GHSA-<script>"),
        ("advisories.0.summary", " "),
        ("advisories.0.severity", None),
        ("advisories.0.affected", "garbage"),
        ("advisories.0.affected", ">= 1.0.0, nonsense"),
        ("advisories.0.fixed", "soon"),
        ("advisories.0.cve_ids", ["CVE-1"]),
        ("advisories.0.url", "javascript:alert(1)"),
    ],
)
def test_a_feed_the_app_would_drop_is_refused(path: str, value: Any) -> None:
    with pytest.raises(security_feed.FeedError):
        security_feed.validate(_broken(path, value))


def test_more_advisories_than_the_app_reads_are_refused() -> None:
    feed = copy.deepcopy(FEED)
    feed["advisories"] *= security_feed.MAX_ADVISORIES + 1
    with pytest.raises(security_feed.FeedError):
        security_feed.validate(feed)


def test_an_advisory_without_affected_versions_is_refused() -> None:
    with pytest.raises(security_feed.FeedError):
        security_feed.from_github([{**GITHUB_ADVISORY, "vulnerabilities": []}], GITHUB_RELEASE)


def test_without_a_feed_file_the_build_asks_github(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    def answer(url: str) -> Any:
        asked.append(url)
        return [GITHUB_ADVISORY] if "security-advisories" in url else GITHUB_RELEASE

    monkeypatch.delenv("OW_SECURITY_FEED")
    monkeypatch.setattr(security_feed.release_source, "_json", answer)
    assert security_feed.load() == FEED
    assert asked == [
        "https://api.github.com/repos/openwhistle/OpenWhistle/security-advisories"
        "?state=published&per_page=100",
        "https://api.github.com/repos/openwhistle/OpenWhistle/releases/latest",
    ]


def test_an_unreachable_github_fails_the_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(url: str) -> Any:
        raise security_feed.release_source.ReleaseError(url)

    monkeypatch.delenv("OW_SECURITY_FEED")
    monkeypatch.setattr(security_feed.release_source, "_json", down)
    with pytest.raises(security_feed.FeedError):
        security_feed.load()


def test_the_build_publishes_the_feed() -> None:
    assert json.loads((built() / "security.json").read_text(encoding="utf-8")) == FEED


@pytest.mark.parametrize("content", ['{"schema": 2}', "not json"])
def test_a_broken_feed_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    feed = tmp_path / "feed-in.json"
    feed.write_text(content, encoding="utf-8")
    monkeypatch.setenv("OW_SECURITY_FEED", str(feed))
    site = builder()
    with pytest.raises(site.BuildError, match="security.json"):
        site.write_security_feed(tmp_path)
    assert not (tmp_path / "security.json").exists()


def test_the_cli_writes_what_github_says(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security_feed, "fetch", lambda: FEED)
    out = tmp_path / "security.json"
    assert security_feed.main([str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == FEED
    assert security_feed.main([]) == 2
