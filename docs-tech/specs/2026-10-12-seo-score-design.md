# SEO score per keyword

Explanation and decision record. A maintainer tool that scores how well a page targets its keyword, so the site can be
walked page by page and each text change measured before and after.

## Decision

| Question | Decision |
| --- | --- |
| Scoring | **yoastseo** (npm, GPL-3.0, Yoast's own analysis): one score 0-100 per page and keyword, with its findings |
| Technical SEO | **Lighthouse** (npm, Google): SEO category per page, optional (`--lighthouse`), it needs Chromium |
| Real effect | Google Search Console, read by the maintainer (or via Claude in Chrome); not part of the tool |
| Built here | only the glue: fetch a page, fill Yoast's `Paper`, print; no scoring logic of our own |
| Rejected | Seobility (3 checks a day, bot wall), Semrush (10 keywords, account), a scorer of our own |

Spike, 2026-10-12, live site: `/de/` "Hinweisgebersystem Software" 83, `/en/` "open source whistleblower software" 81,
comparison article "Hinweisgebersystem Anbieter Vergleich" 76. All three miss the keyword in the first paragraph and
in every H2/H3.

## Shape

```text
tools/seo/
  package.json        yoastseo, lighthouse: exact versions, package-lock.json committed, Renovate updates them
  seo-score.mjs       the CLI
  seo-score.test.mjs  node --test, on fixture HTML
```

| Call | Does |
| --- | --- |
| `npm --prefix tools/seo run score` | every row of the keyword map: page + primary keyword, live site |
| `… -- --secondary` | adds every secondary keyword of each row |
| `… -- --url /de/ --keyword "HinSchG Software"` | one ad-hoc pair |
| `… -- --keyword "…"` | that keyword against every page of `sitemap.xml`, best page first |
| `… -- --base http://127.0.0.1:8901` | the local build (`docs-tech/local-review.md`) instead of openwhistle.net: measure before deploying |
| `… -- --json out.json` / `--compare old.json` | save a run; print the change per row against a saved one |
| `… -- --lighthouse` | adds the Lighthouse SEO score per page |

## Input

The keyword map table in `docs-tech/seo-marketing.md` is the one source. A row whose Page cell is not one backticked
path starting with `/` (today: the English blog twins) is skipped and named in the output, never guessed. Secondary
keywords are the comma-separated cell, without the trailing prose ("as differentiator").

## Page to `Paper`

| Paper field | From |
| --- | --- |
| text | the HTML inside `<main>` after its `<h1>`; WordPress analyses content without the title |
| `title`, `description` | `<title>`, `<meta name="description">` |
| `slug`, `permalink` | the URL |
| `locale` | `<html lang>`: `de_DE` or `en_US`, with the matching Yoast researcher |
| `titleWidth` | estimated at 9 px per character (`shortcut:` in the code; Yoast measures pixels in its editor) |

Removed from the score: **keyphrase in slug**. URLs stay stable; a changed URL costs its ranking even with a redirect.

## Output

One line per row: page, keyword, score, then every finding under 9 of Yoast's points, worst first. Exit 0 whatever
the scores: a score is advice for a writer, not a gate. Exit 1 when a page cannot be fetched or has no `<main>`. No CI
job runs it against the live site.

## Limits, stated in the output's footer

- German: Yoast matches exact word forms only; word-form data is Yoast Premium. "Hinweisgebersysteme" is not a match.
- The score is on-page only. Whether Google rewards a change shows in Search Console, four weeks after deploy
  (`seo-marketing.md`).

## Tests

`node --test tools/seo` in the CI "Tests" job, `npm ci` before it. Covered: keyword map parsing (skipped rows,
secondary cell), `Paper` fields from a fixture page, the slug check removed, `--compare` arithmetic. New guards go
through the mutation audit (`docs-tech/mutations/v2.2.1-site-seo-score.json`).

## Then: the site walk

1. Run against live, save `before.json`.
2. Per page, worst score first: change title, first paragraph, one H2, alt text; build locally; `--base` until the page
   is green or the change would read worse. A text a reader trips over is not worth a point.
3. Merge, release, rollout; run live with `--compare before.json`.
4. Four weeks later: Search Console positions against the table in `seo-marketing.md`.

Known from the spike: `/en/`'s title does not start with its primary, though the keyword map says every title does.
