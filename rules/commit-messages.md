# Commit message prose

Read this when composing a commit message that carries a body, planning or rebuilding a commit series, or reviewing commit messages. The always-loaded core carries the baseline: house-style detection, subject shape and length, footers, security-neutral wording, no AI traces. This module governs the prose itself — when a body exists and what may stand in one. Every rule here is style-agnostic: whether the repo dresses subjects as `type(scope): summary` or as a plain capitalized sentence changes nothing below, and the same body text serves both.

## When a body is written at all

- Default: none. In repos at the scale of vue, vite, and nest, roughly seven commits in ten carry no body — the subject and the diff are the whole message.
- A body earns its place only by carrying what a competent reader cannot derive from the diff: an outside constraint (a platform behaves badly, an API answers ambiguously), a decision that looks wrong without the explanation, an incident the change prevents from happening again, or a policy the code cannot state (what is deliberately left alone, what is never undone).
- Scaffolding, configuration, icons, translations, and documents get no body, and neither does anything whose subject already says everything.
- Shape: at most four paragraphs, wrapped under 80 columns, ordered problem, mechanism, decision. The bodies the core requires (breaking change, security fix, data migration, revert) follow the same shape.

## What never stands in a body

- Enumeration of members: a sentence that names a category stops there — the diff carries which three rules and which six checks ("Three rules are stricter than the preset: no explicit any, hooks at top level, console limited to error" → "A few rules are stricter than the preset"). This holds even when the members are non-obvious edge cases; if a test pins them, the test is where they belong. Delete the paragraph outright when the subject already said it.
- Explaining a competent reader's vocabulary: a mechanism whose name carries its purpose is named, never explained — pinning LF, a lockfile beside its manifest, an atomic temp-file rename, a debounce. Same for a guarantee of the language or type system (an exhaustive match, a union a renderer cannot forget).
- The consequence half: a clause restating what the first half already means is one thing said twice ("Every colour the UI uses has a name in the theme mapping, and no component writes a hex value" → stop after "mapping").
- An explanatory colon: a colon introduces a command block or a real list, never joins a claim to its explanation — that is two sentences.
- A second contrast frame: state what the code does, and contrast with what it does not do ("rather than", "instead of", "not X but Y") at most once per message — 47 uses across 66 commits is a fingerprint, not a style. Where the rejected alternative carries the reason, give it its own sentence.
- An invented past: in a commit that introduces its files, "used to", "previously", and "no longer" describe history the repository does not have — a false statement, not a style problem. Rewrite as the hypothetical it is ("Pushing a few hundred commits would otherwise spawn a few hundred processes"). In a commit changing existing code, past tense is correct and stays.
- Stacked reasons: one reason per sentence — a chain of so, which, and because is two sentences, and three reasons behind one decision is one reason plus noise; keep the one that decided it.
- A count that can be recounted: a number the code enforces stays (a depth cap, a history window, a concurrency limit, a timeout, an HTTP status, a version floor) — it cannot drift without the code drifting with it; a number describing the current shape of the code rots on the next edit ("bumps it in all four version files" → "bumps every version file"). A surviving number is written as digits, including 0–9 and at the start of a sentence (200 commits, 8 at a time), except where it is not data ("one place every git client agrees on"). A count in a subject is fine when the commit fixes it forever ("translate the interface into ten more locales").
- A reference outward: a body stands alone — no reference to another commit in a plan, no "as above", no "the reason given at the top"; the reader has `git log` and the diff, and a planning document is not in the repository. A sha or an issue number is different and belongs in a footer.
- Flourish and signposting: delete a sentence whose only job is to say the preceding fact matters ("The evidence ladder is the whole point"), an opener that announces what is about to be said, and the cleft that inflates a plain statement ("The noreply address is what lets a profile commit privately" → "The noreply address lets a profile commit privately"). The filler and inflation catalog of `rules/markdown.md` applies in full: simply, robust, seamless, comprehensive, "it is worth noting", summary stamps, the forced group of three.

## Characters

- Plain ASCII throughout: no em dash, no arrow glyph, no curly quote, no ellipsis character, no emoji, no non-breaking space — they break `git log`, changelog parsers, and terminals, and they read as machine output.
- No backticks anywhere; identifiers are written bare (profiles.json, ssh-keygen, user.useConfigOnly). Quoting is for the rare string that has to be marked off, and then single quotes.
- No implementation trivia in prose: not an address template, not an include condition, not a full command line, not a call with its argument object — name the thing in words.

## What must survive the cut

Every rule above removes text; this section wins on contact. A body anchored to something that actually happened is the opposite of machine writing — cut a sentence because a reader could have derived it, never because it is long or because a rule above matches its shape.

- Incident provenance: "a standing timer once made this NaN" — past tense here is not invented history; it justifies a present decision.
- Operational knowledge of a live third party that cost real time to learn: which status a host answers to a duplicate key, which greeting closes with a non-zero exit, which browser tries IPv6 first.
- A deliberate refusal: what the change will not do, and why — an option left alone, an identity not restored because it cannot be known.
- A constant with its reason: "200 commits, far enough back to catch a long-wrong identity and short enough to stay instant" — the code enforces the number and the clause says what it buys.
- A wire-format note: field names or spellings shared with data already on disk — nothing in the diff says they cannot be renamed.
- A security boundary: why a check runs before the response is written, why a listener binds both address families.
- Never write a claim into a message to satisfy a rule here: everything stated is confirmed against the code first (core Verification gate). A rewritten sentence that no longer matches the code is a worse defect than the wordiness it replaced.

## Rhythm

- Vary the paragraph opening: half the paragraphs starting on "The" is a rhythm a reader feels before naming it.
- Vary sentence length: a body of uniform 20-word compounds with a comma before "so" reads as generated even when every fact in it is true.

## Checklist

Run over a drafted message before proposing it, then ask the three questions.

```bash
grep -n '`'                        # backticks - must be empty
grep -nP '[^\x00-\x7F]'            # non-ASCII - must be empty
grep -c 'rather than\|instead of'  # contrast frame - at most 1
grep -n 'used to\|previously'      # only in a commit changing existing code
grep -nE '\b(two|three|four|six|ten|twelve) [a-z]+'  # each hit a code-enforced constant
```

- Could a competent developer have derived this sentence from the diff? Yes → delete it.
- Could this paragraph sit unchanged in a hundred other commits in a hundred other repositories? Yes → it says nothing about this change; delete it.
- Is every remaining claim confirmed against the code, or assumed while rewriting? The survival section outranks every deletion rule above it.
