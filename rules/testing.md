# Testing strategy

Read this when writing or restructuring tests, or deciding what kind of test a change needs.

<!-- Distilled from khasky/testing-strategy-playbook and khasky/backend-architecture-playbook; load-testing practice from Slack engineering's continuous load testing. -->

- Placement ladder: unit tests for pure logic, transformations, and policy decisions; integration tests where systems meet (database, queue, cache, HTTP handlers) — against real infrastructure in containers where practical; E2E for a handful of business-critical paths only, never the default answer to a coverage gap.
- Mock external services only, never your own app; a test with more mocking than logic verifies the mock (shared rule with `rules/code-review.md`).
- Assert behavior, not implementation trivia: a test that breaks on a rename without a behavior change tests the wrong thing.
- Test data: factories/builders for readable setup; small fixtures with clear intent; seed data owned by the test — no shared mutable state across suites.
- A flaky test is a defect: report and quarantine it visibly; never silently re-run until green and call it passing (core Verification rule — repeated here because tests are where it bites).
- Coverage is a weak signal for spotting untested areas, never a target; fewer tests with strong assertions beat high coverage with shallow checks. Budget generated tests: 3–5 focused cases per unit (valid, invalid, edge) — more only for a named risk, never padding.
- When mocking an outbound call, assert the request too, not only the canned response: an intercepted request's body/params carry the serialization bugs a mocked response hides.
- Validate API responses against a schema (the contract's own, or one written in the ecosystem's schema validator) instead of property-by-property assertions — a structural check catches the field nobody thought to assert (`rules/api-contracts.md`).
- One test runner per package: extend the incumbent, never introduce a second runner without a migration plan.
- E2E harness boots its own servers: let the test runner start the app and wait on a real readiness URL (`/healthz`) before tests — never a fixed `sleep`, and reuse an already-running server locally so the loop stays fast.
- CI-aware knobs gated on the CI environment variable: fail on a committed focused test, a small retry count, a single worker, trace/video on first retry — so CI catches a stray focused test and a flake leaves a trace, while local stays fast.
- Provide dummy env fallbacks in CI (a throwaway API key, a fake signing secret) so lint/typecheck/build/unit run without real secrets; real credentials gate only the jobs that truly need them.
- Deterministic pure functions (seeded RNG, no wall-clock) are the cheapest thing to unit-test — assert same input produces same output.
- Freeze time and pin the timezone wherever a test touches dates: inject a clock or use the runner's fake timers, and set `TZ=UTC` for the suite. A test that passes only in your timezone, or only before midnight, is a flake with a schedule.
- Database-backed tests isolate per test, not per suite: a transaction rolled back at teardown, or a schema/database per worker. Shared rows plus parallel workers produce failures that depend on execution order and vanish on re-run — the exact signature that gets misread as infrastructure noise.
- A bug fix ships with a test that fails without the fix and passes with it — run it both ways and report both (core Verification rule). A regression test that was green on its very first run has proven nothing yet.
- A "ready for load" or latency claim needs a load test at realistic concurrency against production-like infrastructure, measuring p95/p99 — never the average. Re-run it on a schedule or in CI, not once before launch: capacity regressions arrive with ordinary commits.
- Anything that parses untrusted bytes — a parser, deserializer, codec, upload handler, protocol reader — earns a property or coverage-guided fuzz test, with the seed corpus committed as fixtures so a found crash stays covered.
- Keep a standing hostile-input fixture set (oversized, empty, unicode and RTL, null bytes, deeply nested, duplicate keys) rather than inventing edge cases per test; a crash found by fuzzing is triaged to root cause, never deduplicated away by stack trace (`rules/backend-security.md`).

## JS/TS specifics

- The incumbent runner is Vitest in new TypeScript, Jest where it is already established.
- Playwright owns the E2E lifecycle: `webServer` starts the app against a readiness URL, `reuseExistingServer: !CI` keeps local runs fast.
- Gate the CI knobs on `process.env.CI`: `forbidOnly`, `retries`, `workers: 1`, `trace: 'on-first-retry'`.
