"""A mutation-audit entry whose `old` text no longer occurs in its file guards
nothing: the audit can only report it as stale. Every entry of every live spec must
match its file exactly once, so a change that moves a guard fails here, in the change
that moved it.

Live is a property of this repository, not of the app's releases (ruling, 2026-10-09):
a spec stays live until a website change retires it with a `"history"` reason. An app
release never turns this file red.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
_VERSION = re.compile(r"v(\d+)\.(\d+)\.(\d+)(?:-[\w-]+)?\.json")


def _version(name: str) -> tuple[int, ...]:
    found = _VERSION.fullmatch(name)
    assert found, f"mutation spec name is not vX.Y.Z[-topic].json: {name}"
    return tuple(int(part) for part in found.groups())


ALL_SPECS = sorted((ROOT / "docs-tech" / "mutations").glob("*.json"))
SPECS = [p for p in ALL_SPECS if "history" not in json.loads(p.read_text())]


def test_every_spec_name_carries_a_version() -> None:
    for spec in ALL_SPECS:
        _version(spec.name)


def test_a_retired_spec_says_why_and_a_live_one_remains() -> None:
    for spec in ALL_SPECS:
        reason = json.loads(spec.read_text()).get("history", "x")
        assert isinstance(reason, str) and reason.strip(), spec.name
    assert SPECS, "every spec is history: the guards of this repository go unaudited"


@pytest.mark.parametrize("spec", SPECS, ids=lambda p: p.name)
def test_every_mutation_matches_its_file_exactly_once(spec: Path) -> None:
    stale = []
    data = json.loads(spec.read_text())
    # "manual" entries are run by hand (they need a rebuilt image); their text must still match.
    for m in data["mutations"] + data.get("manual", []):
        target = ROOT / (m.get("file") or m["path"])
        if "create" in m:  # the audit adds this file, so it must not exist yet
            count = 0 if target.exists() else 1
        else:
            count = target.read_text().count(m["old"]) if target.exists() else 0
        if count != 1:
            stale.append(f"{m.get('id') or m.get('name')}: {target.relative_to(ROOT)} x{count}")
    assert not stale, stale


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda p: p.name)
def test_every_id_names_one_mutation(spec: Path) -> None:
    """The audit is run by id: a duplicate runs both, and a report line cannot tell them apart."""
    data = json.loads(spec.read_text())
    ids = [m.get("id") or m.get("name") for m in data["mutations"] + data.get("manual", [])]
    assert not (dups := sorted({i for i in ids if ids.count(i) > 1})), dups


def test_a_spec_cannot_name_a_file_outside_the_repo() -> None:
    from scripts.mutation_audit import inside_root

    assert inside_root("docs/_data/config.yml")
    for bad in ("/etc/passwd", "../outside.txt", "docs/../../outside.txt"):
        assert not inside_root(bad), bad


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda p: p.name)
def test_every_spec_file_is_inside_the_repo(spec: Path) -> None:
    from scripts.mutation_audit import inside_root

    for m in json.loads(spec.read_text())["mutations"]:
        name = m.get("file") or m["path"]
        assert inside_root(name), f"{m.get('id') or m.get('name')}: {name}"


def test_the_audit_reports_red_green_and_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The audit itself, on a stand-in repository: a caught, an uncaught, a stale, an outside, a
    created mutation and one whose file is gone, and every file restored afterwards."""
    from scripts import mutation_audit

    (tmp_path / "tests").mkdir()
    (tmp_path / "a.txt").write_text("guarded\nfree\n")
    (tmp_path / "tests" / "test_a.py").write_text(
        "from pathlib import Path\n\n\n"
        "def test_a():\n"
        "    assert 'guarded' in Path('a.txt').read_text()\n"
        "    assert not Path('extra.txt').exists()\n"
    )
    spec = {
        "test_groups": {"A": ["tests/test_a.py"]},
        "mutations": [
            {"id": "CAUGHT", "file": "a.txt", "old": "guarded", "new": "gone", "tests": "A"},
            {"id": "MISSED", "file": "a.txt", "old": "free", "new": "changed", "tests": "A"},
            {"id": "STALE", "file": "a.txt", "old": "nowhere", "new": "x", "tests": "A"},
            {"id": "OUTSIDE", "file": "../a.txt", "old": "x", "new": "y", "tests": "A"},
            {"id": "CREATED", "file": "extra.txt", "create": "x", "tests": "A"},
            {"id": "EXISTS", "file": "a.txt", "create": "x", "tests": "A"},
            {"id": "GONE", "file": "gone.txt", "old": "x", "new": "y", "tests": "A"},
        ],
    }
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    monkeypatch.setattr(mutation_audit, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["mutation_audit.py", str(tmp_path / "spec.json")])
    assert mutation_audit.main() == 1
    verdicts = {line.split()[0]: line.split()[1] for line in capsys.readouterr().out.splitlines()}
    assert verdicts == {
        "CAUGHT": "RED",
        "MISSED": "GREEN",
        "STALE": "STALE",
        "OUTSIDE": "STALE",
        "CREATED": "RED",
        "EXISTS": "STALE",
        "GONE": "STALE",
    }
    assert (tmp_path / "a.txt").read_text() == "guarded\nfree\n"
    assert not (tmp_path / "extra.txt").exists()


def test_every_audit_run_gets_its_own_bytecode_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two same-length mutations of one module within a second shared a .pyc: the second ran
    the first one's code."""
    import subprocess

    from scripts import mutation_audit

    (tmp_path / "m.py").write_text("VALUE = 1\nOTHER = 2\n")
    spec = {
        "test_groups": {"A": ["tests"]},
        "mutations": [
            {"id": "ONE", "file": "m.py", "old": "VALUE = 1", "new": "VALUE = 3", "tests": "A"},
            {"id": "TWO", "file": "m.py", "old": "OTHER = 2", "new": "OTHER = 4", "tests": "A"},
        ],
    }
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    caches: list[str] = []

    def run(*args: object, **kwargs: dict[str, str]) -> subprocess.CompletedProcess[str]:
        caches.append(kwargs["env"]["PYTHONPYCACHEPREFIX"])
        assert Path(caches[-1]).is_dir()
        return subprocess.CompletedProcess([], 1, "FAILED tests/x.py::t\n", "")

    monkeypatch.setattr(mutation_audit, "ROOT", tmp_path)
    monkeypatch.setattr(mutation_audit.subprocess, "run", run)
    monkeypatch.setattr("sys.argv", ["mutation_audit.py", str(tmp_path / "spec.json")])
    assert mutation_audit.main() == 0
    assert len(set(caches)) == 2 and not any(Path(c).exists() for c in caches)
