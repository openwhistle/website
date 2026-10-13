# Search Console and Bing data in Claude Code

How-to. Connects Claude Code to Google Search Console and Bing Webmaster Tools, read-only, so the
`search-performance` skill (`.claude/skills/search-performance/`) can analyse them.

## Pieces

| File | Does |
| --- | --- |
| `tools/search-console/package.json` + lockfile | pins `search-console-mcp` 2.1.3 and its whole tree; Renovate updates it |
| `.mcp.json` | starts the server from there; credentials only as `${…}` variables |
| `.claude/settings.json` | denies every write tool |
| `tests/test_search_console_mcp.py` | keeps the three in agreement |

Chosen 2026-10-13: the only maintained server that asks Google for `webmasters.readonly` and also reads Bing. No
official Google or Microsoft server exists. Bing's AI Performance (Copilot citations) has no API: export its CSVs.

## Set up once

```sh
npm --prefix tools/search-console ci --ignore-scripts
```

### Google

1. console.cloud.google.com: new project → APIs & Services → enable *Google Search Console API*.
2. IAM → Service Accounts → create (no roles) → Keys → Add key → JSON. Store it outside the repository,
   e.g. `~/.config/openwhistle/gsc-sa.json`, `chmod 600`.
3. Search Console → Settings → Users and permissions → add the service account's e-mail as **Restricted**.

### Bing

1. Bing Webmaster Tools → Settings → API Access → API Key → Generate. The key has full account rights and cannot be
   scoped: the deny list is what keeps Claude read-only on Bing.

### Shell

In the shell that starts Claude Code, never in the repository:

```sh
export GSC_SERVICE_ACCOUNT_FILE="$HOME/.config/openwhistle/gsc-sa.json"
export BING_WEBMASTER_API_KEY=…
```

Start Claude Code in the repository root, approve the `search-console` project server once, check with `/mcp`.

## Known limits

| Limit | Effect |
| --- | --- |
| Bing API has no date range | Bing figures cover Bing's own window |
| Search type fixed to web | no image or news data |
| Several properties on one hostname can mix (upstream issue #110) | keep one property per credential |
| The server checks npm for a newer version once a day and says so in its output | ignore it; Renovate moves the pin |
| A leaked key | Google: delete the key in IAM. Bing: regenerate on the API Access page |
