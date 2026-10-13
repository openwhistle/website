"""The Search Console MCP server runs pinned, takes credentials from the environment, cannot write.

docs-tech/search-console-mcp.md explains the setup; this keeps .mcp.json, the pinned package and the
deny list in .claude/settings.json in agreement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "search-console"
SERVER = "search-console"
# Every tool of search-console-mcp 2.1.3 that changes something at Google or Bing. A version bump
# re-reads its src/index.ts for new ones.
WRITE_TOOLS = (
    "sites_manage",
    "accounts_manage",
    "sitemaps_submit",
    "sitemaps_delete",
    "indexing_submit",
)


def _json(path: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_the_server_runs_from_the_pinned_package() -> None:
    server = _json(ROOT / ".mcp.json")["mcpServers"][SERVER]
    assert server["command"] == "node"
    assert server["args"] == ["tools/search-console/node_modules/search-console-mcp/dist/index.js"]
    pinned = _json(TOOL / "package.json")["dependencies"]["search-console-mcp"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", pinned), "an exact version, never a range"
    locked = _json(TOOL / "package-lock.json")["packages"]["node_modules/search-console-mcp"]
    assert locked["version"] == pinned


def test_every_credential_comes_from_the_environment() -> None:
    env = _json(ROOT / ".mcp.json")["mcpServers"][SERVER]["env"]
    assert env, "no credentials configured"
    for name, value in env.items():
        assert re.fullmatch(r"\$\{[A-Z_]+\}", value), f"{name} is not a ${{VARIABLE}}"


def test_every_write_tool_is_denied() -> None:
    deny = set(_json(ROOT / ".claude" / "settings.json")["permissions"]["deny"])
    missing = [t for t in WRITE_TOOLS if f"mcp__{SERVER}__{t}" not in deny]
    assert not missing, missing
