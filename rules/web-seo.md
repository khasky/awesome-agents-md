# Web SEO essentials

Read this when building, modifying, or auditing public-facing web pages.

<!-- Distilled from AgriciDaniel/claude-seo, nowork-studio/NotFair, coreyhaines31/marketingskills, seb1n seo-optimization; corrected against current guidance (INP replaced FID in 2024; keyword-density advice dropped as dated). hreflang, redirect, and interstitial rules from khasky/marketing-and-seo-playbook. -->

## Indexability first

- Before any other SEO work, verify the page can be indexed: no accidental `noindex`, no robots.txt block, canonical not pointing elsewhere. An unindexable page makes everything else moot — if blocked, lead the report with that.
- Client-side-rendered page with <500 chars of visible text in raw HTML → render it headless before auditing; don't score an empty shell.

## Head

- Exactly one `<title>` per page, ~50–60 chars, unique site-wide; `<meta name="description">` ~150–160 chars, unique. Length bands are SERP-display heuristics — overruns are warnings, not errors. No meta keywords tag (dead).
- `<meta charset="utf-8">` early in `<head>`; `<meta name="viewport" content="width=device-width, initial-scale=1">`; `<html lang>` with a valid BCP-47 tag.
- Self-referencing `<link rel="canonical">` on every indexable page.
- Shareable pages get `og:title`, `og:description`, `og:image` (1200×630) plus Twitter Card tags.
- No synchronous render-blocking `<script>` in `<head>` — use `defer`/`async`/`type="module"`; set `font-display` on webfonts.

## Content structure

- Exactly one H1; H2–H4 nest without skipping levels; headings describe content, not keyword strings.
- Descriptive anchor text (never "click here"); no orphan pages — everything reachable from nav or a hub. Prefer subfolders over subdomains (authority consolidates).
- JSON-LD in `<script type="application/ld+json">` matched to page type: Organization/WebSite sitewide; Article, Product, FAQPage, BreadcrumbList where applicable. Mark up only content visible on the page; validate it.
- Write for people: no keyword stuffing, doorway/thin templated pages, hidden text, or separate AI-targeted content. For AI answers, lead sections with a direct 40–60-word answer.

## Images

- Always `width`/`height` (or `aspect-ratio`) to prevent CLS; `srcset`/`sizes` for responsive; modern formats via `<picture>` (AVIF → WebP → JPEG/PNG fallback).
- `loading="lazy"` below the fold only; never lazy-load the LCP image — preload it.
- Alt text: descriptive, ~10–125 chars on content images; `alt=""` for decorative; never filenames or keyword lists.

## Site level

- XML sitemap of canonical indexable URLs only, referenced from robots.txt; `lastmod` reflects real content changes.
- Never block CSS/JS assets needed for rendering. AI-crawler policy (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) is an explicit decision — blocking prevents AI citation.
- Language/region variants: `hreflang` pairs plus `x-default`; every variant lists the full set including itself.
- Permanent moves get a 301 (never 302); no redirect chains or loops — update internal links to the final URL.
- No full-screen interstitials or overlays covering main content on first paint — mobile ranking penalty; show dialogs after interaction.
- Core Web Vitals, field data at p75: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1. Lab Lighthouse is diagnostic only — never present a lab number as a field result.
