# Contributing to openwhistle.net

Open an issue before a pull request, so the change is agreed before it is built. A change to OpenWhistle itself
belongs in [openwhistle/OpenWhistle](https://github.com/openwhistle/OpenWhistle).

## Development

| Step | Command |
| --- | --- |
| Install | `uv sync --extra dev --extra e2e --group site` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` (CI runs `ruff format --check .`) |
| Types | `uv run mypy --strict scripts` |
| Spelling | `uvx codespell` |
| Workflows | `uvx zizmor --offline .github/workflows` (zero findings) |
| Markdown | `npx --yes markdownlint-cli2 <files>` (rules in `.markdownlint.json`, lines ≤ 120) |
| Tests | `uv run pytest` (reads the latest app release; `OW_APP_SOURCE=<checkout>` works offline) |
| Browser tests | `uv run pytest tests/e2e -m e2e --browser chromium` |

Coverage below 90 % of `scripts/` fails the run. Dependencies are locked in `uv.lock`: after editing
`pyproject.toml`, run `uv lock` and commit both. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/). Code, comments and documentation are English only.

## AI-assisted contributions

Welcome, if they say so. An issue or pull request written by an AI agent begins with:

```markdown
> [!WARNING]
> AI-generated
```

`AGENTS.md` and the templates ask agents for it; `.github/workflows/ai-disclosure.yml` labels what carries it
`ai-generated`. The label is a signal for review, not a block: a bot that ignores instructions is not caught.

## Documentation

There are two kinds, and they are kept apart on purpose.

| | For | Where |
| --- | --- | --- |
| **User documentation** | whoever runs OpenWhistle | `docs/`, published as openwhistle.net |
| **Technical documentation** | whoever maintains this repository | `docs-tech/` and `CLAUDE.md`, **never** published |

`docs/` holds the sources; `scripts/build_site.py` builds them, and nothing outside `docs/` and the app release
reaches the site.

| What | Where |
| --- | --- |
| A page | `docs/<lang>/…` (`.md` for new pages) |
| Strings | `docs/_data/i18n/` |
| Navigation | `docs/_data/nav.yml` |
| Settings reference | `docs/_data/config.yml`: one row per `Settings` field of the latest release |

`test_the_technical_docs_are_not_published` holds that boundary. A page in doubt: would a stranger running
OpenWhistle need it? Yes → `docs/`. Only the next maintainer → `docs-tech/`.

An inline script needs its hash in both CSP lines of `website/nginx.conf` (the test names it). No personal data in
the repository or the image: see [`docs-tech/website-image.md`](docs-tech/website-image.md).

### User pages: maximum information, minimum text

Reach for a diagram before a paragraph, a table before a list of sentences, and a screenshot before a
description of a screen. A thorough page nobody finishes is worth less than a short one that gets read.

| Rule | Held by |
| --- | --- |
| No sentence over 30 words, average under 18 per page | `tests/test_docs_prose.py` |
| Every page of the interface is named in the docs | `tests/test_every_page_is_documented.py` |
| Every setting has one row in `docs/_data/config.yml` | `tests/test_config_documented.py` |

The prose rules cover every page the site builds from a source of its own; generated pages (changelog,
configuration) and the 404 are left out. Code, tables and headings are not counted; inline code is one word. German
abbreviations (`z. B.`, `d. h.`, `bzw.`, `Abs.`) and dates (`2. Juli`) do not end a sentence.

**Diagrams** are draw.io sources in `docs/_diagrams/` (German pages: `<name>.de.drawio`) and
`docs-tech/_diagrams/`, rendered by `scripts/render_diagrams.py` to committed `-light.svg` and `-dark.svg`.
Rules and roles: `docs-tech/diagrams.md`.

**Screenshots are documentation.** They live in `docs/img/screens/<name>-light.png` and `-dark.png`. OpenWhistle's
`scripts/take_screenshots.py` takes them and writes them into a checkout of this repository; they are re-taken in
the change that alters the interface.

### Technical pages: the rule and the incident behind it

Without the incident, a rule gets optimised away at the next rewrite. Never write a dependency version number
there: nothing updates it, and the file holding the pin is one link away.

### A release of OpenWhistle carries its documentation

A user-facing change in OpenWhistle opens a pull request here in the same piece of work, linked from the app's
pull request: settings in `docs/_data/config.yml` and the page that explains them, the guides, screenshots. The
weekly website run fails until the documentation matches the latest release.
