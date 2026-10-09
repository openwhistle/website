"""v1.6.0 deployment facts on the site, against the latest app release."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

import release_source

from tests.built_site import docs_text

ROOT = Path(__file__).parents[1]


def test_the_documented_rollback_downgrades_to_the_last_1_5_revision() -> None:
    """The 1.5.0 image refuses the 1.6 schema: rollback is a downgrade to the
    revision just before 004, run with the 1.6.0 image."""
    (rel,) = [
        f
        for f in release_source.files()
        if PurePosixPath(f).full_match("migrations/versions/004_*.py")
    ]
    before = re.search(r'down_revision: str \| None = "(\w+)"', release_source.read(rel))
    assert before
    upgrade = (ROOT / "docs/en/docs/upgrade/index.html").read_text()
    assert f"alembic downgrade {before.group(1)}" in upgrade


def test_the_docs_run_no_module_that_does_not_exist() -> None:
    files = set(release_source.files())
    for module in re.findall(r"python -m ([\w.]+)", docs_text()):
        path = module.replace(".", "/")
        assert f"{path}/__main__.py" in files or f"{path}.py" in files, module


def test_the_onion_docs_say_to_clear_x_ow_onion_when_an_onion_address_is_set() -> None:
    text = (ROOT / "docs/en/docs/onion/index.html").read_text()
    assert 'proxy_set_header X-OW-Onion "";' in text.replace("\n            ", " ")


def test_no_tracked_file_holds_a_machine_local_path() -> None:
    """A session scratchpad path (user, session id) once reached a public plan."""
    files = (
        subprocess.run(  # noqa: S603
            ["git", "ls-files", "-z"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            check=True,  # noqa: S607
        )
        .stdout.decode()
        .split("\0")
    )
    local = re.compile(r"/tmp/claude-\d+/|/var/home/\w+|/home/jpy\b")  # noqa: S108
    offenders = [
        name
        for name in files
        if name
        and name != "tests/test_v160_ops.py"
        and (ROOT / name).is_file()
        and local.search((ROOT / name).read_bytes().decode("utf-8", "ignore"))
    ]
    assert not offenders, offenders


_PROCESS_NOTE = re.compile(
    r"fix[ -]rounds?\b|\bround[ -]\d\b|\bruling\b|\breviewers?\b|\bre-review|\btask[ -]x?\d"
    r"|chrome[ -](?:review|check) finding",
    re.IGNORECASE,
)

# What this repository ships or publishes: the site sources and the image.
_SHIPPED = re.compile(r"(?:docs|website)/")


def test_shipped_files_explain_the_code_not_the_review_history() -> None:
    """What ships or is published says why the code is like this; "fix round 2"
    or "Task 17" points at review notes the reader of the image or site does
    not have."""
    files = (
        subprocess.run(  # noqa: S603
            ["git", "ls-files", "-z"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            check=True,  # noqa: S607
        )
        .stdout.decode()
        .split("\0")
    )
    offenders = [
        f"{name}: {m.group(0)}"
        for name in files
        if _SHIPPED.match(name) and (ROOT / name).is_file()
        for m in [_PROCESS_NOTE.search((ROOT / name).read_bytes().decode("utf-8", "ignore"))]
        if m
    ]
    assert not offenders, offenders
