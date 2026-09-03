# Comment policy

Read this when writing or reviewing comments, or cleaning up a file's comment style. The always-loaded core carries the baseline (names over comments; remaining comments short, only for non-obvious intent); this module covers what the core leaves out.

Everything here governs comment text: `//`, `/* */`, `/** */`, CSS and JSX comments, and the `//` lines inside `.jsonc` config. None of it touches string literals, template-literal contents, regexes, selectors, CSS values, test titles, assertion messages, fixture values, or any config value — a phrase that breaks a rule below stays exactly as it is inside a string. Rendered user-facing text keeps its own typography (`rules/frontend-design.md`).

## What survives

- The code is authoritative. A comment earns its line only where the logic cannot be traced without it: a non-obvious why, a platform or third-party quirk, an invariant, a safety boundary.
- Delete on sight: restatement of the code or narration of control flow ("check if...", "loop through..."), "this function..." / "this component..." where the name already says it, JSDoc that repeats the signature, step narration inside tests (the test title carries it), any comment defending or praising the design, a bare section label (`// Executor.`), and a cross-reference that resolves to nothing — a deleted planning doc, a dead item number. A comment documenting temporary debugging leaves with the scaffold it describes; where it is a TODO or FIXME, flag it and leave it standing.
- The marker on an intentional simplification survives: a comment naming the known ceiling and the upgrade path ("naive linear scan, index it if the list outgrows a page") is a required annotation, not a comment defending the design (core Coding rule).
- A block over 2 lines is a condense candidate: ask what it tells a reader that the code does not, keep that in 1-2 lines, drop the scene-setting, the history lesson, and the enumerated rejected alternatives. Knowledge that cannot be re-derived from the code — a browser behavior, the reason a workaround exists — survives as one sentence.
- Every checkable claim is verified against the code before it is written or reworded, and a claim you have not confirmed is never written. A redundant comment is noise; a stale one is a lie, and the stale ones a pass uncovers are its most valuable output.
- Name code after the observable role or contract it owns (`apiFetch`, `buildVoteRequestBody`, `retryVoteOrDropAfterLimit`) rather than private infrastructure, implementation mechanics, or internal processing steps.
- Record load-bearing invariants on the type or contract, not only in prose: annotate the field or parameter that must hold the constraint (`// must be square (w === h) for seamless tiling`) where a consumer sees it, so the invariant travels with the code that depends on it.
- In public repos, no comment describes private backend behavior, request-processing internals, abuse-prevention mechanics, operational topology, hidden threat-model assumptions, or how a payload is handled after it leaves the client. The calls and data shapes the public code already shows are not the concern; a comment adding internal detail on top of them is. A deliberately vague comment stays vague, and a reword never introduces a private repo name, auth mechanics, or a live third-party URL or handle.
- When touching existing files, leave the comment style better than you found it: remove obsolete or over-specific comments in the edited area, and rename a helper or local variable when that is the cleaner way to preserve readability.

## How a comment reads

- No mirrored "X, not Y" contrast, and none of its disguises ("X rather than Y", "X instead of Y"). Negative parallelism is the strongest fingerprint of machine writing: state the fact, and where the rejected alternative carries the reason, give it its own clause. `// Rendered from routes, not a second hand-ordered list: the key handler walks the same array` → `// Rendered from routes, the same array the key handler walks, so the arrow keys land on the neighboring item`. Keep a single negative that is itself the rule ("the sender's site must not be trusted"), a list of separate absent signals ("no aria-pressed, no star form"), and plain descriptive English where nothing is being contrasted.
- No stacked negation — a meaning the reader assembles from two negatives. `// Nothing may enter the queue without an owner` → `// Every queue entry carries an owner`. Watch for "not ... not-", "not ... un-", "never ... without", "no ... unless", "must not fail to".
- No padding or hedging words: simply, merely, just as filler, actually, essentially, effectively, basically, really, so far, for now, at this point, in practice, in fact, of course, that said, as such, somewhat, quite, arguably, presumably. Delete them; if deleting changes the meaning, rewrite so the meaning sits in the verb. Keep "just" and "only" where they carry a real restriction ("only the last read counts") or a real time reference ("the button that just vanished").
- No hedging prefixes: `Best-effort:`, `Note:`, `Caveat:`, `Heads-up:`, `For safety:`, `In short:`, `Rule of thumb:`, `Sanity check:`. Delete the prefix and let the sentence start with its own subject. Where "best-effort" is a real mid-sentence predicate, say it in plain words ("these headers are optional").
- A semicolon joining two independent statements becomes two sentences. Keep one only between list items that already contain commas.
- No suffix glued to a searchable name: a file, function, variable, constant, type, CSS class or custom property appears verbatim so it can be pasted straight into a search. `// ci.yml's check job` → `// the check job in ci.yml`; `// getSettings' resolved value` → `// the resolved value of getSettings`. Both apostrophe forms count, including the bare apostrophe a name ending in s takes. A possessive on an ordinary word, a brand, or an acronym is fine.
- No abbreviations: spell them out (SW → service worker, IO → IntersectionObserver, param → parameter, deps → dependency array, prod → production, esp. → especially). Standard industry acronyms stay (DOM, API, HTTP, URL, CSS, HTML, SVG, JSON, UI, OS, TTL, OTP, SPA, WCAG), as do ISO locale codes and established repo vocabulary.
- No number that mirrors a value the code declares: it goes stale silently and nothing fails. `// Drop entries no run has touched in 24h` → `// Drop entries no run has touched within ENTRY_TTL_MS`. Same for a count the reader gets from the array right below the comment ("26 shipped locales", "all 8 fallback selectors") and for a count in prose ("the four first-run steps" → "the first-run steps"). An identifier is not a mirrored number: the human-readable version beside a pinned commit SHA is the only place a reader can see which release was pinned (`rules/ci-cd-security.md`).
- No measured figures — CPU percentages, memory and heap numbers, latency and duration observations, sizes read off a live page, counts of what one run observed, and the provenance stamps that carry them ("measured live", "verified on Windows 10 / Chrome 152"). One machine on one day cannot be re-derived and nothing fails when it drifts, so the measurement goes and the claim it supported stays: `// eight idle triggers cost 17.5% of one core against 0.1% with the spin off` → `// The idle animation is this page's most expensive background cost`. Keep what is not a measurement: protocol and specification constants the code must match (HTTP status codes, a contrast requirement, a storage quota), documented defaults of the tools in use, platform version floors, CSS values the code parses or writes, arithmetic derived from what the code declares, any value that is the literal subject of the data or the test, and the stamp on a value that must be re-tuned as hardware or a threat model moves — a password hashing cost factor carries when it was last tuned, because that date is the condition for re-tuning it (`rules/crypto.md`).
- No numbered spec citations: drop "(WCAG 1.4.10 / 1.4.12)" and its inline forms, including inside JSDoc. Keep a non-numbered mention that names something real, such as a rule-tag set an accessibility scanner accepts, and keep every identifier that resolves to a record — a CVE beside a version pin, an issue or ticket number, an RFC — because it is a pointer to the reason, not a citation of a spec version (`rules/dependencies.md`).
- No parenthesis the sentence reads better without, and no parenthetical identifier the prose already named. Keep a real aside the sentence cannot absorb, an example it needs ("327 555" → "327K"), and a cross-reference that tells the reader where to look.
- Typography is keyboard characters: em and en dash become a plain hyphen or a reword, an ellipsis character becomes three dots, curly quotes become straight, arrows and bullets become a hyphen or a plain word, NBSP and ZWSP become a normal space or go. A stray emoji is deleted; a glyph that is the data the comment documents stays.
- Do not over-compress. A comment that points somewhere must still say what is there, and the clause naming which half of a contract a line covers, or why a timeout has the value it has, is load-bearing. An "after" that reads as a sentence fragment or a bare "see X" was cut too far — give it back its subject. Wording that only parses if the reader is counting ("a fifth tab") reads better generically ("a new tab").

## Never changed by a comment pass

- Behavior. A pass that changes behavior is a failed pass: public API contracts, signatures, exported names, storage keys, message names, request and response shapes, env var names, timeouts, config values, and test expectations stay stable unless the task explicitly requires a functional change.
- Functional directives, wording included, because a tool matches the text or a reviewer needs it verbatim: `biome-ignore`, `eslint-disable`, `@ts-expect-error`, `@ts-check`, SPDX headers, shebangs, `/// <reference>`, `nosemgrep`, test-skip reasons.
- TODO and FIXME. Flag one that looks obsolete; do not resolve or delete it as part of a comment pass.
- A comment inside a string that is injected as code (an in-page evaluation body, a generated file's template): its prose may be fixed under these rules, but never a line of its code and never a value the surrounding code interpolates. A comment in a template that emits a generated file needs the generator re-run, so leave it.
- Line width — never reflow to satisfy a character limit (core rule); the repo's formatter config governs. If a rewrite leaves a ragged short line inside an already-wrapped block, re-wrap that block's own lines and re-read it afterwards to confirm no word was dropped.

## Proving a pass changed nothing

- Do not assert that a pass was comment-only, prove it: print each changed file with comments removed at HEAD and in the working tree, and compare the two outputs — identical output means the diff is comment-only. For CSS, strip `/* */` respecting quoted strings, collapse whitespace, and compare. Files that legitimately differ are the ones where a comment lives inside a template literal; for each of those, show separately that every changed line in the diff is a comment line.
- Then the repo's own gates, read for real output and exit codes rather than a wrapper's summary: lint, typecheck for every config in the repo, and the full unit suite. A single failing run that later runs cannot reproduce is a flake — report it with the evidence, never silently retry until green (core Verification gate).
- Beyond a few thousand comment lines, split the work into partitions along the repo's own directory boundaries, with no file in two partitions — that disjointness is what makes parallel editing safe without a worktree per agent. Each agent gets its exact file scope, these rules, "do exactly this and nothing else", and "do not run lint or tests" so parallel runs cannot collide; verification runs centrally once they finish. An agent that notices a second wording pattern reports it and does not act on it.

## JS/TS specifics

Print the comment-free AST of one file:

```js
// astprint.mjs: print a file's AST with comments removed
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const ts = createRequire(`${process.cwd()}/package.json`)("typescript");
const [file, label] = process.argv.slice(2);
const src = ts.createSourceFile(label, readFileSync(file, "utf8"), ts.ScriptTarget.ESNext,
  false, /\.tsx$/.test(label) ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
process.stdout.write(ts.createPrinter({ removeComments: true }).printFile(src));
```

Compare every changed file against HEAD; any output line names a file whose code, not only its comments, moved:

```bash
for f in $(git diff --name-only | grep -E '\.(ts|tsx|js|mjs)$'); do
  git show "HEAD:$f" > /tmp/head_src
  a=$(node astprint.mjs /tmp/head_src "$f" | md5sum)
  b=$(node astprint.mjs "$f" "$f" | md5sum)
  [ "$a" = "$b" ] || echo "CODE-DIFF $f"
done
```
