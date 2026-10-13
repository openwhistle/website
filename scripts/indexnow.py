"""Tell the IndexNow engines (Bing, Yandex, ...) the URLs of openwhistle.net; run after a rollout.

Reads the live sitemap, checks the live key file, POSTs the URL list. Stdlib only.
Usage: python scripts/indexnow.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

SITE_YML = Path(__file__).resolve().parent.parent / "docs" / "_data" / "site.yml"
ENDPOINT = "https://api.indexnow.org/indexnow"
_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def read_site(path: Path = SITE_YML) -> tuple[str, str]:
    """(base_url, indexnow_key) from site.yml, the one place the key lives."""
    text = path.read_text(encoding="utf-8")
    base = re.search(r"^base_url:\s*(\S+)\s*$", text, re.M)
    key = re.search(r"^indexnow_key:\s*([0-9a-f]{32})\s*$", text, re.M)
    if not base or not key:
        raise SystemExit(f"{path}: base_url or a 32-hex indexnow_key is missing")
    return base.group(1).rstrip("/"), key.group(1)


def sitemap_urls(xml: str) -> list[str]:
    return [loc.text.strip() for loc in ET.fromstring(xml).iter(f"{_NS}loc") if loc.text]  # noqa: S314


def payload(base: str, key: str, urls: list[str]) -> dict[str, object]:
    return {
        "host": urlsplit(base).netloc,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls,
    }


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
        return str(response.read().decode("utf-8"))


def post(endpoint: str, body: dict[str, object]) -> int:
    request = urllib.request.Request(  # noqa: S310
        endpoint,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as error:
        return error.code


def run(base: str, key: str, endpoint: str = ENDPOINT, *, dry_run: bool = False) -> int:
    """0 on 200/202, 1 otherwise (or when the live key file is wrong)."""
    if fetch(f"{base}/{key}.txt").strip() != key:
        print(f"{base}/{key}.txt does not answer with the key: roll out first", file=sys.stderr)
        return 1
    urls = sitemap_urls(fetch(f"{base}/sitemap.xml"))
    body = payload(base, key, urls)
    if dry_run:
        print(json.dumps(body, indent=2))
        return 0
    status = post(endpoint, body)
    print(f"IndexNow: {len(urls)} URLs, HTTP {status}")
    return 0 if status in (200, 202) else 1


def main() -> int:
    base, key = read_site()
    return run(base, key, dry_run="--dry-run" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
