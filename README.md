# openwhistle.net

The website and documentation of [OpenWhistle](https://github.com/openwhistle/OpenWhistle), the open source
whistleblower reporting platform, served at <https://openwhistle.net> from the container image
`ghcr.io/openwhistle/website`.

| Part | Where |
| --- | --- |
| Pages, data, templates, fonts, images | `docs/` (everything here is published) |
| Build | `scripts/build_site.py` → `_site/` |
| Image | `website/` (nginx, read-only, unprivileged), built by `.github/workflows/website-image.yml` |
| Maintainer documentation | `docs-tech/` (never published) |

## What the site documents

The site describes the **latest release** of OpenWhistle, never unreleased work. Its build reads that release
tag (`scripts/release_source.py`: GitHub API and raw.githubusercontent.com, at build time only) and fails when
the documentation no longer matches it:

| From the release | Checked against |
| --- | --- |
| `CHANGELOG.md` | rendered as `/en/changelog/` |
| `app/config.py` (`Settings`, parsed, never imported) | `docs/_data/config.yml`, both ways; the version in the footer and the docs |
| `app/models/report.py`, `app/api/*.py`, `app/i18n.py` | the admin guide's statuses and diagram, every documented page, the language lists |
| `app/static/fonts`, the favicons, the mark, `DESIGN.md` | byte-identical copies here |

The website workflow runs weekly, so a release without its documentation turns red within a week.

## Build locally

```bash
uv sync --extra dev --group site
uv run python scripts/build_site.py                 # the latest release, fetched into .release/
OW_APP_SOURCE=../OpenWhistle uv run python scripts/build_site.py   # a local checkout instead
python -m http.server -d _site 8901
```

Tests: `uv run pytest` (coverage floor 90 % on `scripts/`); browser tests: `uv run pytest tests/e2e -m e2e
--browser chromium`. More in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[GNU General Public License v3.0](LICENSE), like OpenWhistle. Security issues: [SECURITY.md](SECURITY.md).
