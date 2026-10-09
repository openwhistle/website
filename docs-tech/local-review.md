# Local review: checking every page in Chrome

How-to: before a change to the site is merged, an agent (the Claude-in-Chrome extension) checks every
page below visually, in a Full HD window. Playwright at 390 px adds the phone width; it never replaces
the Chrome check. The app's own pages: `docs-tech/local-review.md` in openwhistle/OpenWhistle.

## The page matrix

Every page the site builds. `tests/test_local_review.py` fails if a built page is missing from this
table (parsed from the table rows only, against a floor, so an empty build cannot pass).

### The website (`docs/` sources, built to `_site/`)

Build, then serve the output (the image serves the build, not `docs/`). The legal pages show
their address only in the container (`docs-tech/website-image.md`):

```bash
OW_APP_SOURCE=../OpenWhistle uv run --group site python scripts/build_site.py \
  && python -m http.server -d _site 8901
```

Rebuild after every edit to `docs/`; the server serves what was built. Without `OW_APP_SOURCE`
the build reads the latest app release (`scripts/release_source.py`); with it, the checkout named.

| Page | Notes |
|---|---|
| `/en/` | Landing page, English. |
| `/de/` | Landing page, German — the longest strings; check nothing overflows or truncates. |
| `/en/docs/` | Docs start page — the overview, the "Current version" line, and the sidebar every docs page shares. |
| `/en/docs/requirements/` | Get started: Requirements. |
| `/en/docs/install/` | Get started: Install. |
| `/en/docs/first-report/` | Get started: Your first report. |
| `/en/docs/kubernetes/` | How-to: Kubernetes (Helm). |
| `/en/docs/tls-proxy/` | How-to: TLS proxy. |
| `/en/docs/selinux/` | How-to: SELinux. |
| `/en/docs/onion/` | How-to: Onion address. |
| `/en/docs/ldap/` | How-to: LDAP / AD. |
| `/en/docs/oidc/` | How-to: OIDC. |
| `/en/docs/s3/` | How-to: S3 storage. |
| `/en/docs/clamav/` | How-to: ClamAV. |
| `/en/docs/notifications/` | How-to: Notifications. |
| `/en/docs/retention/` | How-to: Data retention. |
| `/en/docs/multi-tenancy/` | How-to: Multi-tenancy. |
| `/en/docs/upgrade/` | How-to: Upgrade. |
| `/en/docs/rotate-key/` | How-to: Rotate the key. |
| `/en/docs/lost-authenticator/` | How-to: Lost authenticator. |
| `/en/docs/demo-mode/` | How-to: Demo mode. |
| `/en/docs/admin/` | Guides: Admin. |
| `/en/docs/whistleblower/` | Guides: Whistleblower. |
| `/en/docs/configuration/` | Settings reference, generated from `docs/_data/config.yml` — every table scrolls inside its box at 390 px. |
| `/en/docs/images/` | Reference: Images. |
| `/en/docs/roles/` | Reference: Roles. |
| `/en/docs/limits/` | Reference: Attachments. |
| `/en/docs/security-headers/` | Reference: Security headers. |
| `/en/docs/anonymity/` | Explanation: Anonymity layers. |
| `/en/docs/rate-limiting/` | Explanation: Rate limiting. |
| `/en/docs/outbound/` | Explanation: Outbound requests. |
| `/en/docs/timestamps/` | Explanation: Timestamps. |
| `/en/docs/onion-trust/` | Explanation: Onion trust. |
| `/en/docs/redis-sizing/` | Explanation: Redis sizing. |
| `/en/docs/install-count/` | Explanation: Installation count. |
| `/en/docs/security-policy/` | Security policy template, rendered from Markdown in the docs layout. |
| `/en/docs/dpa-template/` | DPA template, rendered from Markdown in the docs layout. |
| `/en/roadmap/` | Roadmap. |
| `/en/compliance/` | Compliance overview: the two law cards; the table stacks into cards at 390 px. |
| `/de/compliance/` | Compliance overview, German. |
| `/en/compliance/eu-directive/` | EU directive: the requirement table stacks into one card per row at 390 px. |
| `/de/compliance/eu-richtlinie/` | EU directive, German. |
| `/en/compliance/hinschg/` | HinSchG: every table stacks into one card per row at 390 px. |
| `/de/compliance/hinschg/` | HinSchG, German. |
| `/en/security/` | Security: the trust table scrolls inside its box at 390 px. |
| `/de/sicherheit/` | Security, German. |
| `/en/contribute/` | Contribute. |
| `/de/mitmachen/` | Contribute, German. |
| `/impressum/` | Imprint, German only — the text is the provider's, word for word; the language switch leads to `/en/`. |
| `/de/datenschutz/` | Privacy policy, German and binding — the "On this page" list sits above the text at 390 px. |
| `/en/privacy/` | Privacy policy, English translation. |
| `/.well-known/security.txt` | Plain text (RFC 9116): `Expires` lies 335 days after the build (RFC 9116: under a year). |
| `/en/blog/feed.xml` | Atom feed (raw XML): every English post, newest first. |
| `/de/blog/feed.xml` | Atom feed, German. |
| `/en/og.png` | Share card (1200×630) — every directory page has its own `og.png`; also open one docs and one German post card. |
| `/en/docs/install/#highlight=docker` | Docs search result: the term is marked and scrolled into view; press `/` for the search dialog. |
| `/en/compare/` | Comparison with GlobaLeaks, SecureDrop, Hush Line — the table scrolls inside its box at 390 px. |
| `/404.html` | Not-found page (noindex); open any missing path on the served site. |
| `/en/changelog/` | Changelog, rendered from the release's `CHANGELOG.md` — check the version nav in the sidebar. |
| `/en/changelog/older/` | The releases before the newest five — the version nav, the link back. |
| `/de/blog/` | Blog index. |
| `/de/blog/hinschg-compliance-leitfaden/` | Article. |
| `/de/blog/hinweisgebersystem-dsgvo-eu-hosting/` | Article. |
| `/de/blog/interne-meldestelle-einrichten/` | Article. |
| `/de/blog/interne-meldestelle-kostenlos/` | Article. |
| `/de/blog/was-ist-neu-in-2-0/` | Article. |
| `/de/blog/whistleblower-software-vergleich/` | Article. |
| `/de/blog/metadaten-entfernen-ohne-beweise-zu-veraendern/` | Article. |
| `/en/blog/` | Blog index, English. Every article below is the English twin of a German one; check the language switch both ways. |
| `/en/blog/hinschg-compliance-guide/` | Article, English. |
| `/en/blog/whistleblowing-system-gdpr-eu-hosting/` | Article, English. |
| `/en/blog/set-up-internal-reporting-channel/` | Article, English. |
| `/en/blog/free-internal-reporting-channel/` | Article, English. |
| `/en/blog/whats-new-in-2-0/` | Article, English. |
| `/en/blog/whistleblowing-software-comparison/` | Article, English. |
| `/en/blog/removing-metadata-without-altering-evidence/` | Article, English. |

## What to check, on every page

- **Both themes**: light and dark (`prefers-color-scheme`, and the in-page toggle itself).
- **Both widths**: 1920 px (Chrome) and 390 px (Playwright) — no sideways scroll.
- **Both languages** where a page has a twin: the language switch leads to it.
- **Console**: no error, and no CSP violation (`Refused to ... because it violates the following
  Content Security Policy directive`) — the image serves a strict CSP without `unsafe-inline`.
- **Interactive paths**, not only the resting state: search (`/`), the docs menu on a phone, the
  theme toggle, the language switch.

Fix every finding in the change that found it — nothing here is carried forward.

## Traps

| Trap | What happens |
|---|---|
| Serving `docs/` instead of `_site/` | `docs/` holds sources (templates, `.md`), not pages. Build first, serve `_site/`; the root-absolute links resolve there. |
| The legal pages show `{address}`-less text | The address is mounted into the container only (`docs-tech/website-image.md`); a local `_site/` shows the include comment. Check those pages once in the container too. |
| A stale release in `.release/` | The cache is keyed by tag; a new app release lands in a new directory. Delete `.release/` to force a fresh fetch. |
