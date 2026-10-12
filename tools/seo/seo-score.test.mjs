import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { paperFields, scorePage } from "./seo-score.mjs";

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
