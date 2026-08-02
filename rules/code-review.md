# Code review

Read this when reviewing a diff/PR or preparing your own changes for review.

## Requesting review

- Package context precisely: BASE and HEAD commits, what the change claims to do, and the plan/requirements it implements — not the full session history.
- PR description answers: what changed, why, risks, how it was tested, where reviewers should focus; UI changes include screenshots; note rollout or follow-up work.
- Prefer small PRs with one coherent intent — split unrelated changes instead of bundling them.
- Review is due before merging any major feature, after complex bug fixes, and before large refactors (to establish a baseline). Never skip it claiming the change is simple.

## Reviewing (two axes)

- Fatal blockers first (doesn't build, doesn't run, broken premise): if one exists, stop scoring details and lead the report with it.
- Spec compliance: does the diff do exactly what was asked — nothing missing, nothing extra?
- Standards: correctness, security, error handling, naming, test quality.
- A diff that adds a trust boundary or data flow (new endpoint, file upload, external integration, queue consumer) or touches auth/payments escalates to security-focused review.
- A diff touching CI workflow files, lockfiles, or build scripts escalates to supply-chain review — those files execute with repository credentials, and they are the least-read code in the repo (`rules/ci-cd-security.md`, `rules/dependencies.md`).
- Tests with more mocking than logic exercise the mock, not the code — flag them. Mock external services only, never your own app.
- A test's existence proves nothing — review what its assertions would catch: an assertion that survives the regression it claims to guard is decoration.
- Architecture findings get names: boundary drift (UI reaching into DB, domain types leaking transport shapes) and one-way doors (schema choices, public API shapes, persisted formats — anything expensive to reverse) are called out explicitly, reversibility stated.
- Diff touches a cache → check the key encodes every variable the value depends on; a cache key missing one input serves user A's data to user B (`rules/caching.md`).
- Fix causes, not symptoms. A "simplification" that requires changing tests is a behavior change in disguise — flag it.
- History is review context: `git log -L <start>,<end>:<file>` on the lines being changed says what the replaced code was for. A line introduced by a commit naming a bug, CVE, or incident is a guard — its removal is a regression until the author says why the cause is gone; a file that keeps appearing in fix commits is a hotspot worth reading whole.
- A confirmed defect is a class, not an instance: before closing the finding, search for the same shape elsewhere — the same sink with another caller, the same missing check on sibling routes, the same pattern copy-pasted into a second module — and report every location as one finding. Fixing the one place the review named leaves the siblings live (core Coding rule on grepping every caller).
- An agent-authored diff earns a plausibility pass a human's would not: confirm every cited file, symbol, flag, and API actually exists, that a claimed verification run really happened and its output says what the summary claims, and that no unrequested file was touched. Fluent prose is not evidence (core Verification gate).
- Label numbers as measured / estimated / unknown; never present an estimate as measured — unknown stays "unknown", not N/A.

## Severity triage

- CRITICAL (blocks merge): data loss, security, broken build — fix immediately.
- HIGH: resolve before proceeding. MEDIUM: note for this cycle. LOW: optional polish.
- Approve only with zero CRITICAL/HIGH findings.
- Disputed feedback: evidence-based pushback only — re-check against the code first, then agree with evidence or object with reasoning.

## Comment format

- One line per finding: `file:line: <severity>: problem. fix.` — location, problem, concrete fix. No throat-clearing ("I noticed that…", "You might want to consider…").
- Concrete fix over "consider refactoring"; exact symbols in backticks; add the why only when the fix isn't obvious from the problem.
- Unsure whether it's a real problem → ask it as a question, never hedge with "perhaps"/"maybe"/"I think".
- Praise once at the top of the review, not per comment.
- Full-prose exceptions: security findings (complete explanation plus reference) and architectural disagreements (rationale, not a one-liner). Resume one-liners after.

## Receiving review

- Read all feedback without reacting; verify each claim against the codebase before implementing — reviewers can lack context, and bots miscount (check a bot's claimed finding count against what you actually fetched).
- Any item unclear → stop and ask before implementing anything. Otherwise implement one item at a time, testing each.
- YAGNI check on suggestions: confirm the suggested thing is actually used or needed before building it.
- Process in severity order; never skip CRITICAL/HIGH without explicit approval. Every comment gets a reply: a fix, evidence-based pushback, or a question.
- Functional fixes commit separately from cosmetic ones.
- Acknowledge factually ("Fixed in <location>"), no thanks or praise; retract your own pushback the same way ("You were right — checked X, it does Y").
