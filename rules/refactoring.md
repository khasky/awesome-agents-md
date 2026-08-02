# Refactoring and cleanup tasks

Read this when the task is a dedicated refactor, cleanup, or "improve this code" pass.

- Refactoring is behavior-preserving. Do not change public behavior, public APIs, persisted formats, routes, event names, config keys, or database schemas unless explicitly requested.
- Match the existing style of the repository before applying generic best practices.
- Small, reviewable passes: rename, remove dead code, simplify control flow (nested conditionals become named predicate functions), extract helper, deduplicate — then verify with the narrowest relevant test, typecheck, lint, or build after each pass.
- Before editing, inspect nearby code and tests to infer naming, error handling, logging, and abstraction patterns.
- No broad rewrites, framework swaps, dependency upgrades, or architectural migrations as part of a cleanup pass.
- Rule of 500: a refactor touching more than ~500 lines is automation work — codemods, AST transforms, scripted rewrites — not hand-editing.
- Mechanical rewrites use a structural tool, never regex: `ast-grep` (pattern and rule syntax in `ast-grep.txt` at the repo root), a codemod, or the language's own refactoring API. A regex edits strings, not syntax, and will eventually rewrite a comment, a string literal, or half an identifier.
- No test coverage on the code being refactored → write the characterization test first: capture current behavior exactly as it is, including the parts that look wrong, then refactor against it. Refactoring untested code is editing in the dark (`rules/testing.md`).
- Chesterton's Fence — before simplifying or deleting, answer: what is this code's responsibility? who calls it and what does it call? which edge cases does it handle? which tests define its behavior? why was it written this way (`git blame`/`git log`)? Can't answer most → not ready to change it.
- Simplification red flags: needing to modify tests (behavior changed, not simplified); removing error handling to make code "cleaner". Simplicity is comprehension speed, not line count.

Done for a refactor means:

- The diff is smaller or clearer than before; behavior is preserved.
- Checks pass per the core Verification gate, or any missing verification is explicitly reported.
- Public API renames are avoided or documented as requiring a separate migration.
- The final response lists files changed, behavior-preservation evidence, and risky areas not touched.
