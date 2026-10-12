// Yoast's SEO analysis per page and keyword (spec: docs-tech/specs/2026-10-12-seo-score-design.md).
import { createRequire } from "node:module";

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
    text: main[1].trim(),
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
