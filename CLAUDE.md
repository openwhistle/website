# openwhistle/website

openwhistle.net: the website and documentation of [OpenWhistle](https://github.com/openwhistle/OpenWhistle), built
from `docs/` by `scripts/build_site.py` and served by the image `ghcr.io/openwhistle/website` (deployed by
wdk-ansible, digest-pinned, cosign-verified).

## Rules

- English only: code, comments, commit messages and every page in `docs-tech/`. The German pages under `docs/de/`
  are the site's German content, not a breach.
- Markdown follows markdownlint (`.markdownlint.json`, lines ≤ 120).
- `CONTRIBUTING.md`, section "Documentation", is binding for every documentation change.
- `docs/` is published, `docs-tech/` never (`test_the_technical_docs_are_not_published`).
- All HTML in `docs/` uses the self-hosted fonts from `docs/_fonts` (inlined by the build) — never Google Fonts or
  any other font CDN. The published site makes no third-party request.
- No personal data in the repository, its history or the image. The operator's address is mounted into the
  container only (`docs-tech/website-image.md`); `OW_PRIVATE_STRINGS` arms the leak guard.
- Commit messages never mention Claude Code.
- Every finding — design, security, privacy, process, any size — is fixed in the work that found it. There is no
  "carried forward" or "out of scope" list; a finding too big for one task is split, never postponed.

## Drift rule (spec S-6)

The site documents the **latest release** of openwhistle/OpenWhistle, read by `scripts/release_source.py`
(`OW_APP_SOURCE=<checkout>` for local work). A user-facing change in the app opens a pull request here in the same
piece of work, linked from the app's pull request. The build and the tests fail when the docs and the release
disagree; the weekly run of `website-image.yml` turns an undocumented release red within a week. Fix the
documentation here — never pin the site to an older release to make it green.

| From the release | Guarded by |
| --- | --- |
| `Settings` of `app/config.py` | `tests/test_config_documented.py` (both ways) |
| `app_version` | footer, docs start page, JSON-LD: `tests/test_v100.py`, `tests/test_seo.py` |
| `ReportStatus`, `STATUS_TRANSITIONS`, routes | `tests/test_release_assets.py`, `tests/test_diagrams.py`, `tests/test_every_page_is_documented.py` |
| fonts, favicons, mark, `DESIGN.md` | `tests/test_release_assets.py` (byte-identical) |

## Before a change is merged

1. `uv run pytest` against the latest release (or the app's release branch via `OW_APP_SOURCE`), coverage ≥ 90 %
   on `scripts/`; ruff, `ruff format --check`, `mypy --strict scripts`, codespell, markdownlint,
   `uvx zizmor --offline .github/workflows` — all clean.
2. Every new guard goes through the mutation audit: a spec in `docs-tech/mutations/vX.Y.Z-site-<topic>.json`
   (X.Y.Z = the app release the work documents), `python scripts/mutation_audit.py <spec>`, all RED.
3. Chrome check: every page of `docs-tech/local-review.md` in the Claude-in-Chrome extension, Full HD, dark first,
   then light; Playwright only adds the 390 px width.
4. Image: `docs-tech/website-image.md` (build, container tests, browser suite against the container).
