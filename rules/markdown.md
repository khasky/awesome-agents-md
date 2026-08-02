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
