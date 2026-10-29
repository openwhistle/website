# Blog sources: add a claim, re-check the sources

How-to. Every blog article backs its claims with a numbered, dated source list; `tests/test_blog_sources.py` holds
the shape. The incident behind it: until 2026-10-27 four of fourteen articles named a retrieval date, the comparison
quoted competitors' prices from a month-old read, and most legal citations linked nothing.

## The shape

```html
… ab 50 Beschäftigten <a class="cite" href="#q1">[1]</a>.
<section class="sources" aria-labelledby="sources-title">
  <h2 id="sources-title">Quellen</h2>
  <ol>
    <li id="q1"><a href="https://…">Title</a>, publisher. Abgerufen am 27.&nbsp;Oktober 2026.</li>
  </ol>
</section>
```

| Rule | Why |
| --- | --- |
| `[n]` before the full stop, not after it | `tests/test_docs_prose.py` would read `.[1] Next` as one sentence |
| One external link per entry; ids `q1`…`qN` in order | the guard checks both |
| Every external link in the body is also a source | a link is a claim; `openwhistle.net` and `github.com/openwhistle/` are exempt |
| Retrieval date not after the article's `modified` | a source read after the update was not what the text was written from |
| German and English twins cite the same URLs | EUR-Lex differs only in `/DE/` vs `/EN/`, which the guard ignores |
| Visible "Aktualisiert am" / "Updated" equals `modified` | the English comparison once said 11 October while its feed said 12 |
| `modified` equals the post's last commit day (UTC) | the sitemap dates a page by git; the v2.4.1 screenshot commit moved the comparison's release row and left `modified` a day behind |

## Re-check before the date moves

Never move a retrieval date without opening the page that day.

1. Fetch every source (`curl -sL -A …`; JS-heavy pages such as BaFin, Cloudflare or Traefik need a browser).
2. Compare each cited fact with the page; change the text where the source moved.
3. Bump the retrieval dates, `modified`, `dateModified` and the visible update line together. Any commit that
   changes a post moves the last three, the release row of the comparison included.
4. `uv run pytest tests/test_blog_sources.py tests/test_hinschg_citations.py --no-cov`.
5. `scripts/check_external_links.py`: a host whose TLS Python cannot negotiate (cipa.jp, 2026-10-27) is reported
   broken every week; cite another page with the same fact instead.

A HinSchG citation needs its section in `SHAPE` of `tests/test_hinschg_citations.py`, counted from
gesetze-im-internet.de. Another law's citation (`… LkSG`, `… OWiG`) needs the law's name in `_OTHER_LAW`.
