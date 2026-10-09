#!/usr/bin/env python3
"""The files of the latest release of openwhistle/OpenWhistle, which this site documents.

    python scripts/release_source.py [--relative]   fetch the release into .release/<tag>/,
                                                    print its path
    python scripts/release_source.py --tag          print the release's tag

The site describes what one can install, so it reads the latest release tag, never `main`
(docs-tech/specs/2026-10-09-website-repo-split-design.md, S-4). The tag is resolved with the
GitHub API (GITHUB_TOKEN is sent when set: unauthenticated runners share 60 requests an hour),
its tree listed once and the files the site reads fetched from raw.githubusercontent.com into
`.release/<tag>/`, which every later build and test reuses until the next release.

OW_RELEASE_TAG=<tag> fetches that tag instead of the latest: the website workflow publishes
exactly the release its test job tested. OW_APP_SOURCE=<directory> replaces the release by a
local checkout: offline work, the app's
unreleased branch, tests. Nothing of the app is ever imported; its Python is parsed with `ast`
(S-5), so the website needs none of the app's packages.
"""

from __future__ import annotations

import ast
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any

REPO = "openwhistle/OpenWhistle"
API = f"https://api.github.com/repos/{REPO}"
RAW = f"https://raw.githubusercontent.com/{REPO}"
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".release"
# What the site reads of a release. The rest of the tree is only listed (tree.txt).
FETCH = (
    "CHANGELOG.md",
    "DESIGN.md",
    "app/**/*.py",
    "app/static/fonts/*",
    "app/static/favicon.svg",
    "app/static/favicon.ico",
    "app/static/apple-touch-icon.png",
    "scripts/*.py",
    "migrations/versions/*.py",
    "charts/openwhistle/values.yaml",
)
TAG = re.compile(r"v\d+\.\d+\.\d+")
_SKIP = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}


class ReleaseError(Exception):
    """The release cannot be read: no network, no tag, or a file the site needs is missing."""


def _get(url: str) -> bytes:
    headers = {"User-Agent": "openwhistle-website-build"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 (fixed https hosts)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return bytes(response.read())
    except OSError as error:
        raise ReleaseError(f"{url}: {error}") from error


def _json(url: str) -> Any:
    return json.loads(_get(url))


def wanted(path: str) -> bool:
    return any(PurePosixPath(path).full_match(pattern) for pattern in FETCH)


def release_tag() -> str:
    """OW_RELEASE_TAG, or the latest release's tag; either must be vX.Y.Z (a path and URL part)."""
    tag = os.environ.get("OW_RELEASE_TAG") or str(_json(f"{API}/releases/latest")["tag_name"])
    if not TAG.fullmatch(tag):
        raise ReleaseError(f"{tag!r} is not a release tag vX.Y.Z")
    return tag


def _cached(dest: Path) -> bool:
    """A whole fetch of this FETCH list: a cache from a shorter list lacks files the site reads."""
    meta = dest / "release.json"
    return meta.is_file() and json.loads(meta.read_text(encoding="utf-8")).get("fetch") == list(
        FETCH
    )


def fetch(cache_dir: Path = CACHE) -> Path:
    """The release in `cache_dir/<tag>/`, downloaded unless it is there already."""
    tag = release_tag()
    dest = cache_dir / tag
    if _cached(dest):
        return dest
    tree = _json(f"{API}/git/trees/{tag}?recursive=1")
    if tree.get("truncated"):
        raise ReleaseError(f"{REPO}@{tag}: the tree listing is truncated")
    paths = sorted(entry["path"] for entry in tree["tree"] if entry["type"] == "blob")
    partial = cache_dir / f"{tag}.partial"
    shutil.rmtree(partial, ignore_errors=True)

    def download(path: str) -> None:
        target = partial / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_get(f"{RAW}/{tag}/{path}"))

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(download, filter(wanted, paths)))  # list(): re-raises a failed download
    commit = _json(f"{API}/commits/{tag}")
    meta = {"tag": tag, "committed": commit["commit"]["committer"]["date"], "fetch": list(FETCH)}
    partial.mkdir(parents=True, exist_ok=True)
    (partial / "tree.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")
    (partial / "release.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    shutil.rmtree(dest, ignore_errors=True)
    partial.rename(dest)  # a half-fetched release is never mistaken for a whole one
    return dest


@cache
def root() -> Path:
    """The directory holding the app's files: OW_APP_SOURCE, or the fetched release."""
    local = os.environ.get("OW_APP_SOURCE")
    if local:
        path = Path(local).resolve()
        if not (path / "app").is_dir():
            raise ReleaseError(f"OW_APP_SOURCE={local}: no app/ directory there")
        return path
    return fetch(CACHE)


def path(rel: str) -> Path:
    found = root() / rel
    if not found.is_file():
        raise ReleaseError(f"{rel}: not in the app source {root()}")
    return found


def read(rel: str) -> str:
    return path(rel).read_text(encoding="utf-8")


def differs(local: Path, rel: str) -> bool:
    """True when `local` is not byte-identical to `rel` of the app source (S-7)."""
    return local.read_bytes() != path(rel).read_bytes()


def files() -> list[str]:
    """Every file of the app source, relative and sorted; a fetched release lists its tree."""
    listing = root() / "tree.txt"
    if (root() / "release.json").is_file():
        return listing.read_text(encoding="utf-8").splitlines()
    return sorted(
        p.relative_to(root()).as_posix()
        for p in root().rglob("*")
        if p.is_file() and not _SKIP & set(p.relative_to(root()).parts)
    )


def changed(rel: str) -> str | None:
    """UTC date of the release's commit (a fetched tag) or of `rel`'s last commit (a checkout)."""
    meta = root() / "release.json"
    if meta.is_file():
        stamp = json.loads(meta.read_text(encoding="utf-8"))["committed"]
        return datetime.datetime.fromisoformat(stamp).astimezone(datetime.UTC).date().isoformat()
    if not (root() / ".git").exists():
        return None  # a copy, not a checkout: a parent repository's dates are not the app's
    run = subprocess.run(  # noqa: S603 (fixed git argv on the configured checkout)
        ["git", "log", "-1", "--format=%ct", "--", rel],  # noqa: S607
        cwd=root(),
        capture_output=True,
        text=True,
        check=False,
    )
    stamp = run.stdout.strip()
    if run.returncode or not stamp:
        return None
    return datetime.datetime.fromtimestamp(int(stamp), datetime.UTC).date().isoformat()


def tag() -> str:
    """The release's tag, or `v<app_version>` for a local checkout."""
    meta = root() / "release.json"
    if meta.is_file():
        return str(json.loads(meta.read_text(encoding="utf-8"))["tag"])
    return f"v{app_version()}"


# ── Python of the app, parsed, never imported ─────────────────────────────


def _module(rel: str) -> ast.Module:
    return ast.parse(read(rel), filename=rel)


def _class(rel: str, name: str) -> ast.ClassDef:
    for node in _module(rel).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise ReleaseError(f"{rel}: no class {name}")


def _literal(node: ast.expr) -> Any:
    # frozenset({...}) and set(...) are calls, not literals; their one argument is
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1:
        if node.func.id in {"frozenset", "set", "tuple", "list"}:
            return ast.literal_eval(node.args[0])
    return ast.literal_eval(node)


def constant(rel: str, name: str) -> Any:
    """A module-level `NAME = <literal>` (or annotated) of the app source."""
    for node in _module(rel).body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            assert isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None
            return _literal(node.value)
    raise ReleaseError(f"{rel}: no constant {name}")


def settings() -> list[str]:
    """The Settings field names of app/config.py, as environment variables (upper case)."""
    return [
        item.target.id.upper()
        for item in _class("app/config.py", "Settings").body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]


def app_version() -> str:
    for item in _class("app/config.py", "Settings").body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.target.id == "app_version"
            and isinstance(item.value, ast.Constant)
        ):
            return str(item.value.value)
    raise ReleaseError("app/config.py: Settings has no app_version")


def enum_values(rel: str, name: str) -> list[str]:
    return [
        str(_literal(item.value)) for item in _class(rel, name).body if isinstance(item, ast.Assign)
    ]


def _str(node: ast.expr, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    return _literal(node)


def routes() -> set[tuple[str, str]]:
    """(method, path) of every route on an `APIRouter` in app/api/*.py.

    Reads `router = APIRouter(prefix=...)`, `@router.get/post/put/delete/patch(path)`,
    `@router.api_route(path, methods=...)` and `router.add_api_route(path, fn, methods=[...])`;
    a `methods=` that names a module-level list is resolved.
    """
    found: set[tuple[str, str]] = set()
    for rel in sorted(f for f in files() if PurePosixPath(f).full_match("app/api/*.py")):
        module = _module(rel)
        names: dict[str, Any] = {}
        prefix = None
        for node in module.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                value = node.value
                if (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "APIRouter"
                ):
                    kw = {k.arg: k.value for k in value.keywords}
                    prefix = _literal(kw["prefix"]) if "prefix" in kw else ""
                    continue
                try:
                    names[target.id] = _literal(value)
                except ValueError:
                    pass
        if prefix is None:
            continue
        calls = [
            dec
            for node in module.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for dec in node.decorator_list
        ] + [n.value for n in module.body if isinstance(n, ast.Expr)]
        for call in calls:
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "router"
            ):
                continue
            verb = call.func.attr
            kw = {k.arg: k.value for k in call.keywords}
            if verb in {"get", "post", "put", "delete", "patch"}:
                methods = [verb.upper()]
            elif verb in {"api_route", "add_api_route"}:
                methods = list(_str(kw["methods"], names)) if "methods" in kw else ["GET"]
            else:
                continue  # include_router and the like register no path of their own
            route = prefix + _str(call.args[0], names)
            found |= {(method, route) for method in methods}
    return found


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        found = root()
        if "--tag" in args:
            print(tag())
        elif "--relative" in args:
            # a path inside the build context, for `docker build --build-arg OW_APP_SOURCE`
            if not found.is_relative_to(Path.cwd()):
                raise ReleaseError(
                    f"{found} is outside {Path.cwd()}: copy it into the build context first"
                )
            print(found.relative_to(Path.cwd()))
        else:
            print(found)
    except ReleaseError as error:
        print(f"release source: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
