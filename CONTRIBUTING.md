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
- Cite where non-obvious material came from in the HTML comment under the heading. Distil in your own words; do not paste licensed text. The comment is optional — a module written from first principles has nothing to cite; never invent a source to fill the slot.

Rule shapes that outperform prose — prefer them when the material allows:

- A correct/wrong pair with the failure mode named ("`getSession()` compiles but trusts an unverified cookie — use `getUser()`") beats an abstract warning.
- A numeric threshold beats an adjective: "nesting ≤ 2, function ≤ 50 lines" is enforceable; "keep it small" is not.
- Version-migration knowledge as old → new pairs (`useFormState` → `useActionState`), not narrative history.
- Where a rule can be checked mechanically, name the command that checks it (a grep, a lint rule, a CI step) — a rule that ships its own enforcement stops being advisory.
- For framework modules, list the APIs and package names models reliably hallucinate or that changed shape in a major version — that blocklist prevents more bugs than another style rule.

## Stack-agnostic, and what that permits

The ruleset holds for any stack with nothing extra to install (README). That is a property of the whole, not of every line: a stack-specific rule is admissible exactly when it cannot fire outside its stack. Four tests decide it.

- The core `AGENTS.md` names a framework, library, or non-baseline CLI only inside an explicit presence check — "A secret scanner is installed (`gitleaks` or similar) →", "a commitlint config always wins". The assumable baseline is git and the OS shell; the core declares no OS as its default either, it matches whichever one the user is on.
- A module names a technology only when its trigger gates the whole module on that technology being present (`rules/nextjs.md`, `rules/rtk.md`, `rules/containers.md`). The rule is then unreachable elsewhere, so the ruleset stays agnostic as a whole.
- The trigger states exactly the scope the content delivers, never wider. A trigger naming three CI platforms over a body covering one, or ending "any framework" over library-specific bullets, is a defect: narrow the trigger or add the missing content. Name the primary technology and where the transfer stops — "Written against husky + lint-staged in a JS/TS repo: the gate rules carry to `pre-commit` and lefthook, the commands do not."
- An ungated module carries no unmarked stack-specific rule. Where general advice needs a concrete API, either give it across ecosystems (`rules/crypto.md`, `rules/dependencies.md`) or move those bullets under an explicit `## <Stack> specifics` heading (`rules/backend-security.md`, `rules/testing.md`, `rules/database.md`).

Never assume a path, file, or configuration belonging to another repository or one machine: "`x.txt` at the repo root" is a rule about someone else's project. Make it conditional or drop it.

## Style

Follow the repo's own `rules/markdown.md` — it applies to this repository first. Short, exact, no filler, no marketing adjectives, commands and paths verbatim.

## Before opening a PR

CI runs the same checks locally in a few seconds:

- `wc -l AGENTS.md` ≤ 200.
- The core names no framework, library, or non-baseline CLI above the module index — a curated blocklist grep, so a tool name that belongs inside a presence check is added to the exception list in the workflow, never waved through.
- Every `rules/*.md` appears in `AGENTS.md`, and every module referenced anywhere exists.
- Relative links resolve and code fences are balanced.

Trigger-versus-content scope is not mechanically checkable — it is the reviewer's job. Read the trigger, then read the bullets, and ask what a reader on a different stack does with each one.

State in the PR which rule the change adds or removes and which mistake it prevents. A PR that adds a module without naming the mistake gets that question back.
