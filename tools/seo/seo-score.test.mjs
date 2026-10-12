import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "node:http";
import { compare, main, paperFields, parseKeywordMap, scorePage } from "./seo-score.mjs";

const html = readFileSync(new URL("./fixtures/page.html", import.meta.url), "utf8");
const url = "https://openwhistle.net/de/";

test("paperFields reads main, title, description, slug and locale", () => {
  const f = paperFields(html, url);
  assert.equal(f.title, "Hinweisgebersystem Software | OpenWhistle");
  assert.match(f.description, /^Hinweisgebersystem Software, kostenlos/);
  assert.equal(f.slug, "/de/");
  assert.equal(f.locale, "de_DE");
  assert.ok(f.text.startsWith("<h1>") && !f.text.includes("Menü"), "only <main> is the text");
});

test("a page without <main> is an error, not a score", () => {
  assert.throws(() => paperFields("<html lang=\"en\"><body>x</body></html>", url), /no <main>/);
});

test("the score is Yoast's, without the slug check", () => {
  const r = scorePage(html, url, "Hinweisgebersystem Software");
  assert.ok(r.score > 0 && r.score <= 100, r.score);
  assert.ok(!r.findings.some((f) => f.id === "slugKeyword"), "URLs stay stable: no slug finding");
  assert.ok(r.findings.some((f) => f.id === "keyphraseInSEOTitle"));
  const scores = r.findings.map((f) => f.score);
  assert.deepEqual(scores, [...scores].sort((a, b) => a - b));
  assert.ok(r.findings.every((f) => !/<[a-z]/i.test(f.text)), "no HTML in a finding");
});

const MAP = `## Keyword map

| Page | Primary | Secondary |
| --- | --- | --- |
| \`/en/\` | open source whistleblower software | free whistleblowing software, HinSchG software |
| \`/de/\` | Hinweisgebersystem Software | HinSchG Software; kostenloses Hinweisgebersystem, Hinweisgebersystem Open Source as differentiator |
| \`blog/en.html\` and the seven English twins | the German page's primary, in English | none yet |

### Search Console evidence
| Query | Clicks |
| --- | --- |
| \`/x/\` | 1 |
`;

test("the keyword map gives page, primary and secondary keywords", () => {
  const { rows, skipped } = parseKeywordMap(MAP);
  assert.deepEqual(rows[0], {
    page: "/en/", primary: "open source whistleblower software",
    secondary: ["free whistleblowing software", "HinSchG software"],
  });
  assert.deepEqual(rows[1].secondary,
    ["HinSchG Software", "kostenloses Hinweisgebersystem", "Hinweisgebersystem Open Source"]);
  assert.equal(rows.length, 2, "only the keyword map table, not the next section's");
  assert.deepEqual(skipped, ["`blog/en.html` and the seven English twins"]);
});

test("the real keyword map parses with at least ten rows", () => {
  const md = readFileSync(new URL("../../docs-tech/seo-marketing.md", import.meta.url), "utf8");
  assert.ok(parseKeywordMap(md).rows.length >= 10);
});

test("a page that is not 200 is an error naming its URL", async () => {
  const server = createServer((req, res) => {
    if (req.url === "/de/") { res.end(html); return; }
    if (req.url === "/sitemap.xml") {
      res.end("<urlset><url><loc>https://openwhistle.net/de/</loc></url></urlset>"); return;
    }
    if (req.url === "/moved/") { res.statusCode = 301; res.setHeader("Location", "/de/"); res.end(); return; }
    res.statusCode = 404; res.end();
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await assert.rejects(main(["--base", base, "--url", "/gone/", "--keyword", "x"]), /\/gone\/ answered 404/);
    await assert.rejects(main(["--base", base, "--url", "/moved/", "--keyword", "x"]), /\/moved\/ answered 301/);
    // --keyword alone: sitemap URLs are rewritten onto --base, never fetched live
    assert.equal(await main(["--base", base, "--keyword", "Hinweisgebersystem Software"]), 0);
  } finally {
    server.close();
  }
});

test("compare gives the change per row; a row new since the old run has no before", () => {
  const before = [{ page: "/de/", keyword: "a", score: 70 }];
  const after = [{ page: "/de/", keyword: "a", score: 83 }, { page: "/en/", keyword: "b", score: 60 }];
  assert.deepEqual(compare(before, after), [
    { page: "/de/", keyword: "a", before: 70, after: 83 },
    { page: "/en/", keyword: "b", before: null, after: 60 },
  ]);
});

test("--json is written before --compare, so a bad compare file does not lose the run", async () => {
  const server = createServer((req, res) => { res.statusCode = req.url === "/de/" ? 200 : 404; res.end(html); });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const file = join(mkdtempSync(join(tmpdir(), "seo-")), "run.json");
  try {
    await assert.rejects(
      main(["--base", base, "--url", "/de/", "--keyword", "Hinweisgebersystem Software", "--json", file,
        "--compare", join(tmpdir(), "missing-seo-run.json")]),
      /ENOENT/,
    );
    assert.ok(existsSync(file), "the run is saved");
    const rows = JSON.parse(readFileSync(file, "utf8"));
    assert.equal(rows.length, 1);
    assert.equal(rows[0].page, "/de/");
  } finally {
    server.close();
  }
});

test("an unreachable base is an error naming its URL", async () => {
  const server = createServer();
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  await new Promise((r) => server.close(r));
  await assert.rejects(main(["--base", base, "--url", "/de/", "--keyword", "x"]), (err) => {
    assert.ok(err.message.startsWith(`${base}/de/: `), err.message);
    return true;
  });
});

test("--json and --compare are relative to where npm was run (INIT_CWD)", async () => {
  const server = createServer((req, res) => { res.statusCode = req.url === "/de/" ? 200 : 404; res.end(html); });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const dir = mkdtempSync(join(tmpdir(), "seo-"));
  const saved = process.env.INIT_CWD;
  process.env.INIT_CWD = dir;
  try {
    const args = ["--base", base, "--url", "/de/", "--keyword", "Hinweisgebersystem Software"];
    await main([...args, "--json", "out.json"]);
    assert.ok(existsSync(join(dir, "out.json")), "written into INIT_CWD");
    assert.equal(await main([...args, "--compare", "out.json"]), 0, "read from INIT_CWD");
  } finally {
    if (saved === undefined) delete process.env.INIT_CWD; else process.env.INIT_CWD = saved;
    server.close();
  }
});

test("flags that would be silently ignored are rejected", async () => {
  await assert.rejects(main(["--url", "/de/"]), /--url needs --keyword/);
  await assert.rejects(main(["--keyword", "x", "--secondary"]), /--secondary works with the keyword map only/);
});

test("a page that never answers times out and names its URL", { timeout: 10_000 }, async () => {
  const server = createServer(() => {}); // accepts, never answers
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  process.env.SEO_FETCH_TIMEOUT_MS = "200"; // the tool's own override; default 30 s
  try {
    await assert.rejects(main(["--base", base, "--url", "/hang/", "--keyword", "x"]), /\/hang\/: TimeoutError/);
  } finally {
    delete process.env.SEO_FETCH_TIMEOUT_MS;
    server.closeAllConnections();
    server.close();
  }
});
