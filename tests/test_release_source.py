"""scripts/release_source.py: the latest app release, fetched once, parsed and never imported.

Everything here runs on tests/fixtures/app_source or a faked GitHub: no network.
"""

from __future__ import annotations

import io
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import release_source

ROOT = Path(__file__).resolve().parents[1]
SITE_FIXTURE = ROOT / "tests" / "fixtures" / "site"


# ── the fixture app source: what the guards read ─────────────────────────


def test_settings_are_the_annotated_fields_in_upper_case(fixture_app: Path) -> None:
    assert release_source.settings() == ["SECRET_KEY", "DEMO_MODE", "APP_VERSION"]
    assert release_source.app_version() == "9.9.9"


def test_constants_are_read_as_literals(fixture_app: Path) -> None:
    assert release_source.constant("app/config.py", "_MIN_SECRET_KEY_LEN") == 32
    assert release_source.constant("app/i18n.py", "_SUPPORTED") == {"en", "de"}
    transitions = release_source.constant("app/models/report.py", "STATUS_TRANSITIONS")
    assert transitions == {"received": {"closed"}, "closed": {"received"}}
    assert release_source.enum_values("app/models/report.py", "ReportStatus") == [
        "received",
        "closed",
    ]


def test_the_fixture_mark_and_favicon_are_the_sites(fixture_app: Path) -> None:
    """The comparison tests/test_release_assets.py makes against the release."""
    assert not release_source.differs(SITE_FIXTURE / "favicon.svg", "app/static/favicon.svg")
    assert release_source.differs(SITE_FIXTURE / "favicon.ico", "app/static/favicon.svg")
    from tests.test_mark import icons

    assert release_source.constant("scripts/render_icons.py", "MARK") == icons.MARK


def test_routes_cover_every_registration_form(fixture_app: Path) -> None:
    assert release_source.routes() == {
        ("GET", "/admin/dashboard"),
        ("POST", "/admin/reports/{report_id}/status"),
        ("GET", "/admin/review-login"),  # methods= names a module-level list
        ("POST", "/admin/review-login"),
        ("GET", "/admin/anything"),  # api_route without methods= is GET
        ("GET", "/submit/{org_slug}"),
        ("POST", "/submit/{org_slug}/restart"),
    }


def test_a_missing_name_or_file_is_a_release_error(fixture_app: Path) -> None:
    with pytest.raises(release_source.ReleaseError, match="no constant NOPE"):
        release_source.constant("app/i18n.py", "NOPE")
    with pytest.raises(release_source.ReleaseError, match="no class Nope"):
        release_source.enum_values("app/models/report.py", "Nope")
    with pytest.raises(release_source.ReleaseError, match="nothing.py: not in the app source"):
        release_source.read("app/nothing.py")


def test_a_settings_class_without_app_version_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "config.py").write_text("class Settings:\n    secret_key: str\n")
    monkeypatch.setenv("OW_APP_SOURCE", str(tmp_path))
    release_source.root.cache_clear()
    try:
        with pytest.raises(release_source.ReleaseError, match="no app_version"):
            release_source.app_version()
    finally:
        release_source.root.cache_clear()


# ── a local checkout (OW_APP_SOURCE) ─────────────────────────────────────


def test_a_checkout_lists_its_files_without_caches(fixture_app: Path) -> None:
    files = release_source.files()
    assert "app/config.py" in files and "CHANGELOG.md" in files
    assert files == sorted(files)
    assert not [f for f in files if "__pycache__" in f]


def test_a_checkout_outside_git_has_no_date_and_its_version_tag(fixture_app: Path) -> None:
    assert release_source.changed("CHANGELOG.md") is None
    assert release_source.tag() == "v9.9.9"


def test_a_git_checkout_dates_a_file_by_its_last_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "CHANGELOG.md").write_text("x\n")
    env = {
        "GIT_COMMITTER_DATE": "2026-10-02T23:30:00+00:00",
        "GIT_AUTHOR_DATE": "2026-10-02T23:30:00+00:00",
    }
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "CHANGELOG.md"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
    ):
        subprocess.run(argv, cwd=tmp_path, check=True, env={**_path_env(), **env})  # noqa: S603
    monkeypatch.setenv("OW_APP_SOURCE", str(tmp_path))
    release_source.root.cache_clear()
    try:
        assert release_source.changed("CHANGELOG.md") == "2026-10-02"
        assert release_source.changed("never-committed.md") is None
    finally:
        release_source.root.cache_clear()


def _path_env() -> dict[str, str]:
    import os

    return {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")}  # noqa: S108


def test_a_directory_without_app_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OW_APP_SOURCE", str(tmp_path))
    release_source.root.cache_clear()
    try:
        with pytest.raises(release_source.ReleaseError, match="no app/ directory"):
            release_source.root()
    finally:
        release_source.root.cache_clear()


# ── the fetch: GitHub faked ───────────────────────────────────────────────

TAG = "v9.9.9"
TREE = [
    "CHANGELOG.md",
    "README.md",
    "app/config.py",
    "app/static/fonts/a.woff2",
    "docs notes/a b.md",  # a space: the listing is one path per line
    "tests/x.py",
]


class _Fake:
    """The GitHub API and raw.githubusercontent.com, as urlopen sees them."""

    def __init__(self, truncated: bool = False, latest: str = TAG) -> None:
        self.truncated = truncated
        self.latest = latest
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> io.BytesIO:
        self.requests.append(request)
        url = request.full_url
        body: Any
        if url == f"{release_source.API}/releases/latest":
            body = {"tag_name": self.latest}
        elif url == f"{release_source.API}/git/trees/{TAG}?recursive=1":
            body = {
                "truncated": self.truncated,
                "tree": [{"path": p, "type": "blob"} for p in TREE]
                + [{"path": "app", "type": "tree"}],
            }
        elif url == f"{release_source.API}/commits/{TAG}":
            body = {"commit": {"committer": {"date": "2026-10-03T23:30:00+02:00"}}}
        elif url.startswith(f"{release_source.RAW}/{TAG}/"):
            return io.BytesIO(url.rsplit("/", 1)[1].encode())
        else:
            raise OSError(f"no such URL: {url}")
        return io.BytesIO(json.dumps(body).encode())


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> _Fake:
    fake = _Fake()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OW_RELEASE_TAG", raising=False)
    return fake


def test_the_fetch_takes_exactly_the_files_the_site_reads(github: _Fake, tmp_path: Path) -> None:
    dest = release_source.fetch(tmp_path)
    assert dest == tmp_path / TAG
    fetched = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    assert fetched == [
        "CHANGELOG.md",
        "app/config.py",
        "app/static/fonts/a.woff2",
        "release.json",
        "tree.txt",
    ]
    assert (dest / "app/config.py").read_text() == "config.py"
    assert (dest / "tree.txt").read_text().splitlines() == TREE
    assert not (tmp_path / f"{TAG}.partial").exists()


def test_a_fetched_release_is_read_by_tag_tree_and_date(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OW_APP_SOURCE", raising=False)
    monkeypatch.setattr(release_source, "CACHE", tmp_path)
    release_source.root.cache_clear()
    try:
        assert release_source.root() == tmp_path / TAG
        assert release_source.tag() == TAG
        assert release_source.files() == TREE  # the whole tree, not only what was fetched
        assert release_source.changed("CHANGELOG.md") == "2026-10-03"  # 21:30 UTC
    finally:
        release_source.root.cache_clear()


def test_a_second_fetch_asks_only_for_the_tag(github: _Fake, tmp_path: Path) -> None:
    release_source.fetch(tmp_path)
    github.requests.clear()
    release_source.fetch(tmp_path)
    assert [r.full_url for r in github.requests] == [f"{release_source.API}/releases/latest"]


def test_a_truncated_tree_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _Fake(truncated=True))
    with pytest.raises(release_source.ReleaseError, match="truncated"):
        release_source.fetch(tmp_path)
    assert not (tmp_path / TAG).exists()


def test_the_token_goes_to_the_api_only(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    release_source.fetch(tmp_path)
    for request in github.requests:
        sent = request.get_header("Authorization")
        api = request.full_url.startswith(release_source.API)
        assert sent == ("Bearer t0ken" if api else None), request.full_url


def test_a_network_error_is_a_release_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def offline(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        raise OSError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", offline)
    with pytest.raises(release_source.ReleaseError, match="releases/latest: offline"):
        release_source.fetch(tmp_path)


# ── the command line ─────────────────────────────────────────────────────


def test_main_prints_the_source_absolute_or_relative(
    fixture_app: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert release_source.main([]) == 0
    assert capsys.readouterr().out.strip() == str(fixture_app)
    monkeypatch.chdir(ROOT)
    assert release_source.main(["--relative"]) == 0
    assert capsys.readouterr().out.strip() == "tests/fixtures/app_source"


def test_main_reports_a_release_error_as_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OW_APP_SOURCE", str(tmp_path))
    release_source.root.cache_clear()
    try:
        assert release_source.main([]) == 1
    finally:
        release_source.root.cache_clear()
    assert "no app/ directory" in capsys.readouterr().err


def test_a_pinned_tag_is_fetched_without_asking_for_the_latest(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The publish job builds the tag its test job tested, not whatever is latest by then."""
    github.latest = "v10.0.0"
    monkeypatch.setenv("OW_RELEASE_TAG", TAG)
    assert release_source.fetch(tmp_path) == tmp_path / TAG
    assert f"{release_source.API}/releases/latest" not in [r.full_url for r in github.requests]


@pytest.mark.parametrize("bad", ["../../etc", "v1.2", "main", "v1.2.3/../x", "v1.2.3\n"])
def test_a_tag_that_is_no_release_version_is_refused(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    github.latest = bad
    with pytest.raises(release_source.ReleaseError, match="is not a release tag"):
        release_source.fetch(tmp_path)
    monkeypatch.setenv("OW_RELEASE_TAG", bad)
    with pytest.raises(release_source.ReleaseError, match="is not a release tag"):
        release_source.fetch(tmp_path)
    assert not any(tmp_path.iterdir())


def test_a_cache_fetched_with_another_list_is_fetched_again(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release_source.fetch(tmp_path)
    monkeypatch.setattr(release_source, "FETCH", (*release_source.FETCH, "README.md"))
    github.requests.clear()
    dest = release_source.fetch(tmp_path)
    assert (dest / "README.md").is_file()
    assert f"{release_source.API}/git/trees/{TAG}?recursive=1" in [
        r.full_url for r in github.requests
    ]


def test_main_prints_the_tag(fixture_app: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert release_source.main(["--tag"]) == 0
    assert capsys.readouterr().out.strip() == "v9.9.9"


def test_relative_outside_the_working_directory_fails_loudly(
    fixture_app: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty --build-arg would let the image build fetch the latest release instead."""
    monkeypatch.chdir(tmp_path)
    assert release_source.main(["--relative"]) == 1
    assert "is outside" in capsys.readouterr().err


@pytest.mark.parametrize("broken", ["", '{"tag": "v9.9', "[]", "\xff\xfe"])
def test_a_corrupt_cache_is_fetched_again(github: _Fake, tmp_path: Path, broken: str) -> None:
    dest = release_source.fetch(tmp_path)
    (dest / "release.json").write_bytes(broken.encode("latin-1"))
    github.requests.clear()
    assert release_source.fetch(tmp_path) == dest
    assert json.loads((dest / "release.json").read_text())["tag"] == TAG
    assert f"{release_source.API}/git/trees/{TAG}?recursive=1" in [
        r.full_url for r in github.requests
    ]


def test_a_non_ascii_digit_is_no_release_tag(
    github: _Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OW_RELEASE_TAG", "v\u0662.1.1")  # ARABIC-INDIC DIGIT TWO
    with pytest.raises(release_source.ReleaseError, match="is not a release tag"):
        release_source.fetch(tmp_path)


def test_tag_asks_for_the_latest_release_once(
    github: _Fake,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OW_APP_SOURCE", raising=False)
    monkeypatch.setattr(release_source, "CACHE", tmp_path)
    release_source.root.cache_clear()
    try:
        assert release_source.main(["--tag"]) == 0
    finally:
        release_source.root.cache_clear()
    assert capsys.readouterr().out.strip() == TAG
    latest = [r for r in github.requests if r.full_url.endswith("/releases/latest")]
    assert len(latest) == 1
