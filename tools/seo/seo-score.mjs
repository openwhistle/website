// Yoast's SEO analysis per page and keyword (spec: docs-tech/specs/2026-10-12-seo-score-design.md).
import { createRequire } from "node:module";
import { readFileSync, realpathSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const require = createRequire(import.meta.url);
const { Paper, SeoAssessor } = require("yoastseo");
const { build } = require("yoastseo/build/parse/build");
const LanguageProcessor = require("yoastseo/build/parse/language/LanguageProcessor.js").default;
const RESEARCHERS = {
  de: require("yoastseo/build/languageProcessing/languages/de/Researcher").default,
  en: require("yoastseo/build/languageProcessing/languages/en/Researcher").default,
};
const LOCALES = { de: "de_DE", en: "en_US" };
// URLs stay stable: a changed URL costs its ranking even with a redirect.
const IGNORED = ["slugKeyword"];

const unescape = (s) =>
  s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
const pick = (html, re) => unescape((html.match(re) || [, ""])[1]);

export function paperFields(html, url) {
  const main = html.match(/<main\b[^>]*>([\s\S]*)<\/main>/);
  if (!main) throw new Error(`no <main> in ${url}`);
  const lang = pick(html, /<html[^>]*\blang="([a-z]{2})/);
  const title = pick(html, /<title>([^<]*)<\/title>/);
  return {
    text: main[1].split(/<\/h1>/)[1]?.trim() ?? main[1].trim(), // WordPress analyses the content, not title or label
    title,
    description: pick(html, /<meta name="description" content="([^"]*)"/),
    slug: new URL(url).pathname,
    permalink: url,
    lang,
    locale: LOCALES[lang] || "en_US",
    // shortcut: Yoast measures the title in pixels in its editor; ~9 px a character until we render it
    titleWidth: title.length * 9,
  };
}

export function scorePage(html, url, keyword) {
  const { text, lang, ...attributes } = paperFields(html, url);
  const paper = new Paper(text, { ...attributes, keyword });
  const researcher = new (RESEARCHERS[lang] || RESEARCHERS.en)(paper);
  paper.setTree(build(paper, new LanguageProcessor(researcher)));
  const assessor = new SeoAssessor(researcher);
  for (const id of IGNORED) assessor.removeAssessment(id);
  assessor.assess(paper);
  const findings = assessor
    .getValidResults()
    .map((r) => ({ id: r.getIdentifier(), score: r.getScore(), text: r.getText().replace(/<[^>]+>/g, "") }))
    .sort((a, b) => a.score - b.score);
  return { score: assessor.calculateOverallScore(), findings };
}

const MAP_FILE = new URL("../../docs-tech/seo-marketing.md", import.meta.url);

export function parseKeywordMap(markdown) {
  const section = markdown.split(/^## Keyword map$/m)[1]?.split(/^#{2,3} /m)[0] ?? "";
  const rows = [];
  const skipped = [];
  for (const line of section.split("\n").filter((l) => l.startsWith("| ")).slice(2)) {
    const [page, primary, secondary] = line.split("|").slice(1, -1).map((c) => c.trim());
    const path = page.match(/^`(\/[^`]*)`$/);
    if (!path) { skipped.push(page); continue; }
    rows.push({
      page: path[1],
      primary,
      secondary: secondary
        .split(/[,;]/)
        .map((k) => k.replace(/\bas differentiator\b.*$/, "").trim())
        .filter((k) => k && !/^none\b/.test(k)),
    });
  }
  return { rows, skipped };
}

async function fetchPage(url) {
  let res;
  try {
    res = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(Number(process.env.SEO_FETCH_TIMEOUT_MS) || 30_000) });
  } catch (err) {
    throw new Error(`${url}: ${err.cause?.code ?? err.name ?? err.message}`);
  }
  if (res.status !== 200) throw new Error(`${url} answered ${res.status}`);
  return res.text();
}

export async function run(pairs, base) {
  const cache = new Map();
  const out = [];
  for (const { page, keyword } of pairs) {
    const url = new URL(page, base).href;
    if (!cache.has(url)) cache.set(url, await fetchPage(url));
    out.push({ page, keyword, ...scorePage(cache.get(url), url, keyword) });
  }
  return out;
}

async function sitemapPages(base) {
  const xml = await fetchPage(new URL("/sitemap.xml", base).href);
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname);
}

export function compare(before, after) {
  const old = new Map(before.map((r) => [`${r.page}\0${r.keyword}`, r.score]));
  return after.map((r) => ({
    page: r.page, keyword: r.keyword, before: old.get(`${r.page}\0${r.keyword}`) ?? null, after: r.score,
  }));
}

async function lighthouseSeo(url) {
  let lighthouse, chromeLauncher;
  try {
    ({ default: lighthouse } = await import("lighthouse")); // optional dependency
    chromeLauncher = await import("chrome-launcher");
  } catch (err) {
    if (err.code !== "ERR_MODULE_NOT_FOUND") throw err;
    throw new Error("lighthouse is not installed: run npm --prefix tools/seo ci (it is an optional dependency)");
  }
  const chrome = await chromeLauncher.launch({ chromeFlags: ["--headless=new"] });
  try {
    const r = await lighthouse(url, { port: chrome.port, onlyCategories: ["seo"], logLevel: "error" });
    return Math.round(r.lhr.categories.seo.score * 100);
  } finally {
    await chrome.kill();
  }
}

function print(results, skipped) {
  for (const r of results) {
    console.log(`${String(r.score).padStart(3)}  ${r.page}  "${r.keyword}"`);
    for (const f of r.findings.filter((f) => f.score < 9)) console.log(`       ${f.score}  ${f.text}`);
  }
  for (const s of skipped) console.log(`skipped: ${s} (not one page path)`);
  console.log(
    "\nOn-page only; Search Console shows whether Google rewards a change. German: exact word forms only " +
      "(word-form data is Yoast Premium). Not scored: keyphrase in slug (URLs stay stable)."
  );
}

export async function main(argv) {
  const { values: o } = parseArgs({
    args: argv,
    options: {
      base: { type: "string", default: "https://openwhistle.net" },
      url: { type: "string" },
      keyword: { type: "string" },
      secondary: { type: "boolean", default: false },
      json: { type: "string" },
      compare: { type: "string" },
      lighthouse: { type: "boolean", default: false },
    },
  });
  if (o.url && !o.keyword) throw new Error("--url needs --keyword");
  if (o.secondary && o.keyword) throw new Error("--secondary works with the keyword map only, not with --keyword");
  // npm runs in tools/seo; INIT_CWD is where the user ran it
  const here = (f) => resolve(process.env.INIT_CWD ?? process.cwd(), f);
  let pairs;
  let skipped = [];
  if (o.keyword && o.url) pairs = [{ page: o.url, keyword: o.keyword }];
  else if (o.keyword) pairs = (await sitemapPages(o.base)).map((page) => ({ page, keyword: o.keyword }));
  else {
    const map = parseKeywordMap(readFileSync(MAP_FILE, "utf8"));
    skipped = map.skipped;
    pairs = map.rows.flatMap((r) =>
      [r.primary, ...(o.secondary ? r.secondary : [])].map((keyword) => ({ page: r.page, keyword })));
  }
  const results = await run(pairs, o.base);
  if (o.keyword && !o.url) results.sort((a, b) => b.score - a.score);
  print(results, skipped);
  if (o.json) writeFileSync(here(o.json), JSON.stringify(results, null, 1)); // before anything that can fail
  if (o.compare) {
    for (const c of compare(JSON.parse(readFileSync(here(o.compare), "utf8")), results)) {
      const delta = c.before === null ? "new" : `${c.after - c.before >= 0 ? "+" : ""}${c.after - c.before}`;
      console.log(`${String(c.after).padStart(3)} ${delta.padStart(4)}  ${c.page}  "${c.keyword}"`);
    }
  }
  if (o.lighthouse) {
    for (const page of [...new Set(results.map((r) => r.page))])
      console.log(`Lighthouse SEO ${String(await lighthouseSeo(new URL(page, o.base).href)).padStart(3)}  ${page}`);
  }
  return 0;
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(
    (code) => process.exit(code),
    (err) => { console.error(`error: ${err.message}`); process.exit(1); },
  );
}
