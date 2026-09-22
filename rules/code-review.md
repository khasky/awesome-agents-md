# Code review

Read this when reviewing a diff/PR or preparing your own changes for review.

## Requesting review

- Package context precisely: BASE and HEAD commits, what the change claims to do, and the plan/requirements it implements — not the full session history.
- PR description answers: what changed, why, risks, how it was tested, where reviewers should focus; UI changes include screenshots; note the rollout steps this change itself requires.
- Prefer small PRs with one coherent intent — split unrelated changes instead of bundling them.
- The description is written for a reviewer who never saw the conversation that produced the change: lead with what the change does and the resulting behavior, give a trigger and a before/after where one clarifies, and scale the detail to the change — two sentences plus the validation is a complete description of a small PR.
- Open on the change, not the breakage: one or two sentences in the imperative of the diff ("Adds a check for characters no reader can see", "Passes the rewind reason the script requires"), and the problem second. A description that opens on the failure reads as an incident report and buries what is being merged.
- A description persists, so it carries no line numbers, no byte offsets or counts, and no totals the next commit invalidates ("1596 tests, same as before"). Name the file, the symbol and the suite instead: a pin sends the next reader to unrelated code with full confidence, and a test total is stale the day someone adds a test (core Communication rule on persisted text).
- Third person, neutral: not "I did not run it" but "the integration suite was not run"; never "you can check it by" or "worth knowing if you touch that line". A description states the change — it is neither advice addressed to the reviewer nor a report of the author's session, and the forensic aside that reconstructs how the defect was found ("the last green run finished 79 minutes before the guard landed") belongs in neither.
- Leave out what the pipeline already does. "Checked with lint, typecheck and the unit suite" restates what every PR runs; state only verification a reviewer could not assume — a probe that had to be constructed, or a lane deliberately skipped and why.
- Leave out branch coordination: merge order, what this is stacked on, which sibling lands first. That is operator traffic for the chat or the merge queue, and it is wrong the moment either branch moves. Findings the change does not fix go to the tracker, not to a "still open" section that turns a reviewable diff into a status report.
- Machine-written shape to drop: headings on a PR of a few files, bold-lead bullets, a table for a handful of rows, a numbered list of the commits the host already renders, em dashes (`rules/markdown.md`).
- One paragraph is one line, however long it runs. The commit convention that wraps a body under 80 columns exists because `git log` reflows nothing; a review host reflows to whatever width the reader has, so a hard wrap there pins the text to a column no reader shares, leaves a ragged edge on every other viewport, and has to be redone by hand after each edit. The same holds for a description written into an issue, a release note or a tracker.
- Generating the body → generate it through a check that refuses to write when it finds `:[0-9]+`, first or second person, a non-ASCII character, or two prose lines in a row (a paragraph that survived as one line cannot produce them). Catching it before upload costs one run; catching it after costs an edit on every open PR.
- Scope drifted during the work → rewrite the title and description around what was actually built, and drop the abandoned approaches. A history of what you tried belongs in the PR only where it explains a tradeoff the reviewer has to judge.
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
- Review the diff, not the repository: a defect the change introduced is a finding, a pre-existing one is a separate note the author can decline. Neither is a demand for rigor the rest of the codebase doesn't carry — validation and comment density the surrounding files never had is a proposal, not a blocker.
- "This might break something elsewhere" is not a finding until you name the code it breaks. Speculation costs the author the search you skipped.
- Fix causes, not symptoms. A "simplification" that requires changing tests is a behavior change in disguise — flag it.
- A comment in the diff is a claim: check it against the code it sits on. One that no longer describes that code is a defect, not a nit, and the machine-written tells (mirrored "X, not Y", figures from one measurement) are findings of their own (`rules/code-comments.md`).
- History is review context: `git log -L <start>,<end>:<file>` on the lines being changed says what the replaced code was for. A line introduced by a commit naming a bug, CVE, or incident is a guard — its removal is a regression until the author says why the cause is gone; a file that keeps appearing in fix commits is a hotspot worth reading whole.
- A confirmed defect is a class, not an instance: before closing the finding, search for the same shape elsewhere — the same sink with another caller, the same missing check on sibling routes, the same pattern copy-pasted into a second module — and report every location as one finding. Fixing the one place the review named leaves the siblings live (core Coding rule on grepping every caller).
- An agent-authored diff earns a plausibility pass a human's would not: confirm every cited file, symbol, flag, and API actually exists, that a claimed verification run really happened and its output says what the summary claims, and that no unrequested file was touched. Fluent prose is not evidence (core Verification gate).
- Label numbers as measured / estimated / unknown; never present an estimate as measured — unknown stays "unknown", not N/A.

## Severity triage

- CRITICAL (blocks merge): data loss, security, broken build — fix immediately.
- HIGH: resolve before proceeding. MEDIUM: note for this cycle. LOW: optional polish.
- Approve only with zero CRITICAL/HIGH findings.
- Disputed feedback: evidence-based pushback only — re-check against the code first, then agree with evidence or object with reasoning.

## Review comment format

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
