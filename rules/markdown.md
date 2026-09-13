# Markdown editorial rules

Read this when editing Markdown documents: docs, articles, READMEs.

- Preserve facts, links, citations, code blocks, commands, and YAML frontmatter.
- Do not invent sources, numbers, quotes, dates, or personal experience.
- Prefer specific, direct prose over generic summaries.
- Remove chatbot artifacts, placeholders, excessive bold, decorative formatting, and empty conclusions.
- Replace vague headings with concrete headings.
- Delete paragraphs that add no fact, instruction, example, or decision.
- Return concise diff summaries. Do not add generic praise.
- Quoted examples and cited text stay byte-identical — even when they contain patterns banned below.
- Consistency pass: uniform terminology, heading capitalization, and number style across the document.
- One H1 per document; heading levels descend without skipping (never H2 straight to H4), and heading text is unique within the file so generated anchors don't collide.
- Every code fence declares a language after the opening backticks (`ts`, `bash`, `json`) — highlighting, copy buttons, and downstream tooling all key off it; use `text` when the block has no language.
- Links to files inside the same repository are relative (`rules/testing.md`), not absolute URLs to the hosting provider — a relative link survives forks, mirrors, and an org rename. Exception: files whose format specification requires absolute URLs (`llms.txt`).
- Images and diagrams carry alt text describing what a reader who cannot see them would otherwise miss, never the filename.
- Never hard-wrap prose to a column limit: one paragraph is one line and the renderer wraps it. Reflowing turns a one-word edit into a whole-paragraph diff (core rule against wrapping to satisfy a character count).
- Editing feedback names the location and the concrete fix ("'it' in §2 is ambiguous — name the subject"), never bare adjectives ("unclear").
- At most two em-dashes per paragraph. Mix sentence lengths deliberately; flag sentences over ~30 words.
- Merge bullet lists where 3+ items share the same opening words or rhythm. Compress fillers: "in order to" → "to", "due to the fact that" → "because".
- Not every claim needs a "however" — drop performative balance.
- A heading is followed by content, never by a sentence restating the heading. `## Performance` then `Speed matters.` then the real point: delete the middle line, which is a rhetorical warm-up that reads as padding.
- A document describes what the thing is, not what changed about it. Cut prose narrating its own last revision ("has been updated to", "now uses", "previously") outside the genres that are version-scoped by definition: changelogs, release notes, migration guides.
- No word claiming a choice was intended — "deliberately", "intentionally", "on purpose", "by design" about the document's own subject, and the same four in comment text and commit messages (`rules/code-comments.md`). The reason is what shows the intent: "The marker is deliberate: it proves the import chain works" → "The marker proves the import chain works" (`rules/code-comments.md` carries the same rule for code comments).
- No aphorism formulas — "X is the Y of Z", "the language of", "the currency of", "the architecture of", "X becomes a trap". They dress an ordinary claim as a maxim without adding precision. State the claim the formula is gesturing at.
- One short sentence for emphasis is fine; three or more clipped fragments in a row is manufactured drama. Break the run by restoring a full clause, not by shortening the neighbours.
- Hyphenate a compound only where it sits before the noun: `a high-quality report`, `a data-driven decision`, but `the report is high quality`, `the decision is data driven`. Uniform hyphenation in both positions is a machine tell; the attributive-only rule is what people actually write.
- Headings default to sentence case. Title Case On Every Heading is a tell in prose documents; follow the repo's existing convention where it has one, and never switch conventions inside a document.

Avoid these patterns unless the document's house style requires them:

- "It is important to note"
- "In conclusion"
- "Overall"
- "This guide explores"
- "plays a crucial role"
- "seamless", "robust", "cutting-edge", "pivotal"
- "delve", "tapestry", "testament to", "embark on a journey"
- figurative "navigate" / "landscape" / "realm"; "leverage" as a verb
- "holistic", "paramount", "state-of-the-art"; "comprehensive" where "complete" works
- "Generally speaking", "In essence", "At its core", "It's worth mentioning"
- sentence-initial "Furthermore," / "Moreover,"
- forced groups of three
- "not only X but also Y"
- tiny tables that should be prose

Not a violation — leave these alone:

- A quoted source, a cited title, or a fixture that contains a banned phrase. Quoted text is evidence and stays byte-identical; the ban covers what the document says in its own voice.
- Em-dashes and long sentences in prose the repository publishes as writing rather than as reference: an essay, a post, a personal README. The two-per-paragraph bar is for documentation.
- A sentence fragment used deliberately in marketing copy or a pull-quote. Ask the author before normalizing a register they chose.
- A table whose rows genuinely carry parallel fields. "Tiny tables that should be prose" targets a table of one column, not a short table of real data.
- Title Case inside a proper name, a product name, a book or paper title, or a heading the project's existing house style already sets that way.
- "deliberately", "by design" and their siblings describing something the document did not choose: a platform's behavior ("hooks are bypassable by design"), a register another author picked, an adverb of manner in an instruction ("mix sentence lengths deliberately"). The ban covers a document defending its own decisions.
- A repeated word where the alternative is a synonym the reader has to map back. Term consistency outranks variety in reference documents.
