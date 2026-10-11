#!/usr/bin/env python3
"""Counts the website's page views from its IP-less `counter` log (redesign spec D5).

journalctl CONTAINER_NAME=openwhistle-website -o cat --since -7d | python scripts/site_stats.py
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Iterable

_ASSET_SUFFIXES = (
    ".css",
    ".js",
    ".png",
    ".svg",
    ".woff2",
    ".avif",
    ".webp",
    ".xml",
    ".txt",
    ".json",
    ".ico",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".map",
    ".woff",
    ".webmanifest",
)


def count(lines: Iterable[str]) -> tuple[Counter[str], Counter[str]]:
    pages: Counter[str] = Counter()
    refs: Counter[str] = Counter()
    for line in lines:
        parts = line.split()
        # 304 too: Cache-Control no-cache revalidates, so a revisit is a 304, not a 200.
        if len(parts) != 4 or parts[2] not in {"200", "304"}:
            continue
        _time, uri, _status, ref = parts
        # Skip assets and pagefind; only count pages and their referrers
        if uri.startswith("/pagefind/") or uri.endswith(_ASSET_SUFFIXES):
            continue
        # $uri logs a page as its index file; strip /index.html only as a path segment
        if uri.endswith("/index.html"):
            uri = uri.removesuffix("index.html")
        pages[uri] += 1
        if ref != "-":
            refs[ref.lower()] += 1  # nginx logs the Referer's host as sent
    return pages, refs


def main() -> int:
    pages, refs = count(sys.stdin)
    print("Pages")
    for uri, n in pages.most_common():
        print(f"{n:8} {uri}")
    print("\nReferrer hosts")
    for host, n in refs.most_common():
        print(f"{n:8} {host}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
