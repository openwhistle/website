"""tools/seo is JavaScript: its node:test suite runs here, so CI and the mutation audit reach it."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "seo"


def test_the_seo_tool_passes_its_node_tests() -> None:
    if not (TOOL / "node_modules").is_dir():
        pytest.fail("run `npm --prefix tools/seo ci` first", pytrace=False)
    node = shutil.which("node")
    assert node, "node is not installed"
    run = subprocess.run([node, "--test"], cwd=TOOL, capture_output=True, text=True, timeout=300)  # noqa: S603
    assert run.returncode == 0, run.stdout[-4000:] + run.stderr[-2000:]
    # node --test exits 0 when its file pattern finds no test file at all.
    ran = re.search(r"^(?:# |ℹ )tests (\d+)$", run.stdout, re.M)
    assert ran and int(ran[1]) > 0, run.stdout[-2000:]
