"""IndexNow: the key file of the built site, and scripts/indexnow.py against a local fake."""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import indexnow
import pytest

from tests.built_site import ROOT, built

BASE, KEY = indexnow.read_site()
SITEMAP = (
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://openwhistle.net/en/</loc></url>"
    "<url><loc>https://openwhistle.net/de/</loc></url></urlset>"
)


def test_the_built_site_serves_the_key_from_the_one_source() -> None:
    assert re.fullmatch(r"[0-9a-f]{32}", KEY)
    assert (built() / f"{KEY}.txt").read_text(encoding="utf-8") == KEY
    assert (ROOT / "docs/_data/site.yml").read_text().count(KEY) == 1
    assert KEY not in (ROOT / ".github/workflows/indexnow.yml").read_text()


def test_the_key_file_is_not_in_the_sitemap() -> None:
    assert KEY not in (built() / "sitemap.xml").read_text(encoding="utf-8")


def test_sitemap_urls_and_payload_shape() -> None:
    urls = indexnow.sitemap_urls(SITEMAP)
    assert urls == ["https://openwhistle.net/en/", "https://openwhistle.net/de/"]
    assert indexnow.payload(BASE, KEY, urls) == {
        "host": "openwhistle.net",
        "key": KEY,
        "keyLocation": f"{BASE}/{KEY}.txt",
        "urlList": urls,
    }


def test_a_site_yml_without_a_key_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "site.yml"
    broken.write_text("base_url: https://x.example\nindexnow_key: nope\n")
    with pytest.raises(SystemExit):
        indexnow.read_site(broken)


class _Fake:
    """One local server: the live site (key, sitemap) and the IndexNow endpoint."""

    def __init__(self, key_body: str, answer: int) -> None:
        self.posted: list[dict[str, object]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                body = key_body if self.path.endswith(".txt") else SITEMAP
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body.encode())

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers["Content-Length"])
                fake.posted.append(json.loads(self.rfile.read(length)))
                self.send_response(answer)
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.mark.parametrize(
    ("answer", "code"), [(200, 0), (202, 0), (403, 1), (422, 1), (429, 1), (500, 1)]
)
def test_run_succeeds_only_on_200_and_202(answer: int, code: int) -> None:
    fake = _Fake(KEY, answer)
    try:
        assert indexnow.run(fake.base, KEY, f"{fake.base}/indexnow") == code
    finally:
        fake.close()
    assert fake.posted[0]["urlList"] == [
        "https://openwhistle.net/en/",
        "https://openwhistle.net/de/",
    ]
    assert fake.posted[0]["key"] == KEY


def test_a_wrong_live_key_file_posts_nothing() -> None:
    fake = _Fake("something else", 200)
    try:
        assert indexnow.run(fake.base, KEY, f"{fake.base}/indexnow") == 1
    finally:
        fake.close()
    assert fake.posted == []


def test_dry_run_posts_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    fake = _Fake(KEY, 500)
    try:
        assert indexnow.run(fake.base, KEY, f"{fake.base}/indexnow", dry_run=True) == 0
    finally:
        fake.close()
    assert fake.posted == []
    assert json.loads(capsys.readouterr().out)["key"] == KEY
