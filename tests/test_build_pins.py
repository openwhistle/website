"""Build tool pins that live in several files must agree."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def test_uv_version_is_the_same_in_the_image_and_every_workflow() -> None:
    image = re.search(
        r"ghcr\.io/astral-sh/uv:([0-9.]+)", (ROOT / "website" / "Dockerfile").read_text()
    )
    assert image, "website/Dockerfile no longer copies uv from ghcr.io/astral-sh/uv"
    pins = {
        wf.name: re.findall(r"uv==([0-9.]+)", wf.read_text())
        for wf in (ROOT / ".github" / "workflows").glob("*.yml")
    }
    stale = {name: found for name, found in pins.items() if set(found) - {image.group(1)}}
    assert not stale, f"uv pins differ from website/Dockerfile's {image.group(1)}: {stale}"
    assert any(pins.values()), "no workflow pins uv — the check reaches nothing"


def _all(pattern: str, *globs: str) -> set[str]:
    return {m for g in globs for f in ROOT.glob(g) for m in re.findall(pattern, f.read_text())}


def test_python_version_is_the_same_everywhere() -> None:
    found = _all(r"python:(\d+\.\d+)-slim", "website/Dockerfile")
    found |= _all(r'python-version: "(\d+\.\d+)"', ".github/workflows/*.yml")
    found |= _all(r'requires-python = ">=(\d+\.\d+)"', "pyproject.toml")
    assert len(found) == 1, f"Python versions disagree: {found}"


@pytest.mark.parametrize("dockerfile", ["website/Dockerfile"])
def test_base_images_are_pinned_by_digest(dockerfile: str) -> None:
    images = re.findall(r"^FROM (?:--\S+ )*(\S+)", (ROOT / dockerfile).read_text(), re.M)
    assert len(images) == 2, images
    assert all(re.search(r"@sha256:[0-9a-f]{64}$", f) for f in images), images


def test_every_workflow_action_is_pinned_by_commit_sha() -> None:
    """Every `uses: owner/repo@...` in every workflow must pin a full 40-hex
    commit SHA, with a `# vX...` comment recording the human-readable
    version — never a floating tag/branch (`@v4`, `@main`), which a
    compromised upstream tag could silently repoint. `docker/*-action`,
    `actions/*`, and third-party actions (e.g. `aquasecurity/trivy-action`,
    `DavidAnson/markdownlint-cli2-action`) are all covered; this repository's own
    (`uses: $/...`) is pinned to the running commit by GitHub and is exempt. The
    workspace-relative `./...` loads whatever the job's checkout holds: zizmor
    (self-repository) and this test refuse it."""
    pattern = re.compile(r"^(\s*-?\s*)?uses:\s*(\S+)\s*(#.*)?$", re.M)
    unpinned: dict[str, list[str]] = {}
    refs: list[str] = []
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = wf.read_text()
        for _prefix, ref, comment in pattern.findall(text):
            refs.append(ref)
            if ref.startswith("$/") or ref.startswith("docker://"):
                continue  # this repository at this commit, or an inline image
            bad = []
            if not re.search(r"@[0-9a-f]{40}$", ref):
                bad.append(f"{ref!r} is not pinned to a 40-hex commit SHA")
            elif not re.fullmatch(r"#\s*v[\w.]+\s*", comment):
                bad.append(f"{ref!r} has no '# vX' version comment")
            if bad:
                unpinned.setdefault(wf.name, []).extend(bad)
    assert refs, "no `uses:` line found — the check reaches nothing"
    assert unpinned == {}, unpinned


def test_no_bare_pip_install_in_any_workflow() -> None:
    """A `pip install` (or `uv pip install`) line in a workflow must be
    pinned, not a floating "whatever's latest today" install that bypasses
    uv.lock — the same pinning discipline
    test_every_workflow_action_is_pinned_by_commit_sha enforces for actions.
    Allowed without a version pin: `-r <file>` (a requirements file that was
    itself generated from the lock, e.g. `uv export --frozen`) and `-e .`
    (installing this project from the checkout, which has no separate
    version to pin). Every other package argument must carry `==<version>`.
    """
    pattern = re.compile(r"\bpip install\b(.*)$", re.M)
    bad: dict[str, list[str]] = {}
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        for line in pattern.findall(wf.read_text()):
            if re.search(r"(^|\s)-r\s+\S+", line) or re.search(r"(^|\s)-e\s+\S+", line):
                continue  # requirements file or local editable install
            for token in line.split():
                if token.startswith("-"):
                    continue
                if "==" not in token:
                    bad.setdefault(wf.name, []).append(
                        f"unpinned package {token!r} in 'pip install{line}'"
                    )
    assert bad == {}, bad


def test_security_workflow_audits_dependencies_and_the_image() -> None:
    wf = (ROOT / ".github/workflows/security.yml").read_text()
    needles = (
        "pull_request:",
        "schedule:",
        "pip-audit",
        "aquasecurity/trivy-action@",
        "--all-extras",
        "ghcr.io/openwhistle/website:latest",
    )
    for needle in needles:
        assert needle in wf, needle
    pinned = re.search(r"aquasecurity/trivy-action@[0-9a-f]{40}", wf)
    assert pinned, "trivy action not pinned by digest"
