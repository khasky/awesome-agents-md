# Contributing

## The bar for a new rule

One question decides admission and retention: **would an agent get this wrong without the line?**

- Yes → it belongs.
- No, a competent agent already does it → it does not, however true it is. A rule nobody needed spends attention that the rules below it needed.

The same test prunes. When a model generation stops making a mistake, the line that prevented it becomes a deletion candidate.

## Where a rule goes

`AGENTS.md` is the always-loaded core and is capped at **200 lines**, enforced in CI. That cap is the whole design: frontier models follow roughly 150–200 instructions reliably and the agent's own system prompt already spends some of them. Adding to the core means removing from the core.

Everything conditional goes to `rules/` — a module is read only when the task matches, so it costs nothing until it is needed. A new module needs:

1. The file, `rules/<topic>.md`.
2. One entry in the **On-demand rule modules** list at the end of `AGENTS.md`, naming the trigger ("Read this when …"). CI fails if a module is unlisted or a listed module is missing.
3. One entry in `llms.txt`.

Pack two modules per bullet in the core list where they are related — the list is line-budgeted like everything else.

## Module format

```markdown
# Topic

Read this when <the exact trigger — a task type, not a technology fan club>.

<!-- Distilled from <sources>. -->

- <one rule per bullet, imperative, specific enough to act on>
```

- Every bullet states a decision, a threshold, or a boundary. "Be careful with X" is not a rule; "X is atomic — a read, then a decision, then a write loses to parallel requests" is.
- Cross-reference sibling modules inline as `` (`rules/<sibling>.md`) `` instead of repeating their content. Repeat a rule across modules only when its absence at that moment would cause the mistake, and say why it is repeated.
- Cite where non-obvious material came from in the HTML comment under the heading. Distil in your own words; do not paste licensed text.
- Modules stay stack-agnostic where they can. A framework-specific module is fine (`rules/nextjs.md`) as long as it is gated by its trigger line.
- Nothing tool-specific belongs in the core `AGENTS.md`. A module for a specific CLI is acceptable only if its trigger gates it on that tool being installed.

## Style

Follow the repo's own `rules/markdown.md` — it applies to this repository first. Short, exact, no filler, no marketing adjectives, commands and paths verbatim.

## Before opening a PR

CI runs the same checks locally in a few seconds:

- `wc -l AGENTS.md` ≤ 200.
- Every `rules/*.md` appears in `AGENTS.md`, and every module referenced anywhere exists.
- Relative links resolve and code fences are balanced.

State in the PR which rule the change adds or removes and which mistake it prevents. A PR that adds a module without naming the mistake gets that question back.
