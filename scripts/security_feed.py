#!/usr/bin/env python3
"""/security.json: the latest release and the published security advisories of OpenWhistle.

    python scripts/security_feed.py OUT     fetch from GitHub, validate, write OUT

Every OpenWhistle installation with the update check on (the default since 2.5.0) fetches this
file once a day and nothing else; the format is schema 1 of the app's
docs-tech/security-feed.md. The build writes it (scripts/build_site.py): from OW_SECURITY_FEED,
a file this script wrote earlier in the workflow, or else straight from the GitHub API
(GITHUB_TOKEN is sent when set, as scripts/release_source.py does). Anything the app would drop
fails the build instead: a broken feed is never published.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import release_source

SEVERITIES = {"low", "medium", "high", "critical"}
VERSION = re.compile(r"[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}")  # ASCII digits, as release_source.TAG
CONSTRAINT = re.compile(r"(?:<=|>=|<|>|=)?\s*v?[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}")
GHSA = re.compile(r"GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}")
CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,7}")
MAX_ADVISORIES = 100


class FeedError(Exception):
    """The feed would not pass the app's validation: the build fails instead of publishing it."""


def _https(url: Any, what: str) -> str:
    if not isinstance(url, str) or not url.startswith("https://") or len(url) > 500:
        raise FeedError(f"{what}: {url!r} is not an https URL")
    return url


def _range(value: Any, what: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 200
        or not all(CONSTRAINT.fullmatch(part.strip()) for part in value.split(","))
    ):
        raise FeedError(f"{what}: {value!r} is not a version range")
    return value


def validate(feed: Any) -> dict[str, Any]:
    """The feed unchanged when every field passes; FeedError naming the first that does not."""
    if not isinstance(feed, dict) or feed.get("schema") != 1:
        raise FeedError("not a schema 1 feed")
    latest = feed.get("latest")
    if not isinstance(latest, dict) or not VERSION.fullmatch(str(latest.get("version"))):
        raise FeedError(f"latest: {latest!r} names no version")
    _https(latest.get("url"), "latest.url")
    advisories = feed.get("advisories")
    if not isinstance(advisories, list) or len(advisories) > MAX_ADVISORIES:
        raise FeedError(f"advisories: a list of at most {MAX_ADVISORIES} expected")
    for adv in advisories:
        if not isinstance(adv, dict) or not GHSA.fullmatch(str(adv.get("id"))):
            raise FeedError(f"advisory {adv!r}: no GHSA id")
        what = adv["id"]
        summary = adv.get("summary")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 1024:
            raise FeedError(f"{what}: summary {summary!r}")
        if adv.get("severity") not in SEVERITIES:
            raise FeedError(f"{what}: severity {adv.get('severity')!r}")
        _range(adv.get("affected"), f"{what}.affected")
        fixed = adv.get("fixed")
        if not isinstance(fixed, str) or (fixed and not VERSION.fullmatch(fixed)):
            raise FeedError(f"{what}: fixed {fixed!r} is not a version")
        cves = adv.get("cve_ids")
        if not isinstance(cves, list) or not all(CVE.fullmatch(str(c)) for c in cves):
            raise FeedError(f"{what}: cve_ids {cves!r}")
        _https(adv.get("url"), f"{what}.url")
    return feed


def from_github(advisories: Any, release: Any) -> dict[str, Any]:
    """Schema 1 from GitHub's published repository advisories and its latest release."""
    if not isinstance(advisories, list) or not isinstance(release, dict):
        raise FeedError("GitHub answered with something other than advisories and a release")
    entries = []
    for adv in advisories:
        vulns = adv.get("vulnerabilities") if isinstance(adv, dict) else None
        if not vulns or not isinstance(vulns[0], dict):
            raise FeedError(f"advisory {adv!r}: no affected versions")
        cve = adv.get("cve_id")
        entries.append(
            {
                "id": adv.get("ghsa_id"),
                "cve_ids": [cve] if cve else [],
                "summary": adv.get("summary"),
                "severity": adv.get("severity"),
                "affected": vulns[0].get("vulnerable_version_range"),
                "fixed": vulns[0].get("patched_versions") or "",
                "url": adv.get("html_url"),
            }
        )
    tag = str(release.get("tag_name", ""))
    return validate(
        {
            "schema": 1,
            "latest": {
                "version": tag.removeprefix("v"),
                "url": release.get("html_url"),
                "published_at": release.get("published_at") or "",
            },
            "advisories": entries,
        }
    )


def fetch() -> dict[str, Any]:
    """The feed from the GitHub API now."""
    api = release_source.API
    try:
        return from_github(
            release_source._json(f"{api}/security-advisories?state=published&per_page=100"),
            release_source._json(f"{api}/releases/latest"),
        )
    except release_source.ReleaseError as error:
        raise FeedError(str(error)) from error


def load() -> dict[str, Any]:
    """OW_SECURITY_FEED (validated again: it may have been edited), or a fresh fetch."""
    path = os.environ.get("OW_SECURITY_FEED")
    if not path:
        return fetch()
    try:
        return validate(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        raise FeedError(f"OW_SECURITY_FEED={path}: {error}") from error


def dump(feed: dict[str, Any]) -> str:
    return json.dumps(feed, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        feed = fetch()
    except FeedError as error:
        print(f"security feed: {error}", file=sys.stderr)
        return 1
    Path(args[0]).write_text(dump(feed), encoding="utf-8")
    print(f"{len(feed['advisories'])} advisories, latest {feed['latest']['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
