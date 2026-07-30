# Comment policy

Read this when writing or reviewing comments, or cleaning up a file's comment style.

- Prefer self-descriptive names over explanatory comments. If a comment explains what a function, branch, variable, payload, retry, cache, or state transition does, first try to rename the surrounding code so the comment becomes unnecessary.
- Keep names clear but not verbose. Name code after the observable role or contract it owns (`apiFetch`, `buildVoteRequestBody`, `retryVoteOrDropAfterLimit`) rather than private infrastructure, implementation mechanics, or internal processing steps.
- Comments that remain must be short and simple. Use them only for non-obvious intent, browser/platform constraints, public protocol constraints, or safety boundaries that cannot be expressed cleanly in code.
- Record load-bearing invariants on the type or contract, not only in prose: annotate the field/parameter that must hold a constraint (`// must be square (w === h) for seamless tiling`) where a consumer sees it, so the invariant travels with the code that depends on it.
- In public repos, do not add comments that describe private backend behavior, request-processing internals, abuse-prevention mechanics, operational topology, hidden threat-model assumptions, or how API payloads are handled after they leave the client. The public code may show calls and data shapes, but comments must not add extra internal detail.
- Avoid comments that create a maintenance burden: restating code, narrating tests line by line, documenting temporary debugging, or explaining why a specific private service behaves a certain way. Delete or simplify them before finishing.
- When touching existing files, leave the comment style better than you found it: remove obsolete or over-specific comments in the edited area, and rename helpers/local variables when that is the cleaner way to preserve readability.
- Refactors made for comment cleanup must be behavior-preserving. Keep public API contracts, storage keys, message names, request/response shapes, and test expectations stable unless the task explicitly requires a functional change.
