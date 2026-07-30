# Testing strategy

Read this when writing or restructuring tests, or deciding what kind of test a change needs.

<!-- Distilled from khasky/testing-strategy-playbook and khasky/backend-architecture-playbook. -->

- Placement ladder: unit tests for pure logic, transformations, and policy decisions; integration tests where systems meet (database, queue, cache, HTTP handlers) — against real infrastructure in containers where practical; E2E for a handful of business-critical paths only, never the default answer to a coverage gap.
- Mock external services only, never your own app; a test with more mocking than logic verifies the mock (shared rule with `rules/code-review.md`).
- Assert behavior, not implementation trivia: a test that breaks on a rename without a behavior change tests the wrong thing.
- Test data: factories/builders for readable setup; small fixtures with clear intent; seed data owned by the test — no shared mutable state across suites.
- A flaky test is a defect: report and quarantine it visibly; never silently re-run until green and call it passing (core Verification rule — repeated here because tests are where it bites).
- Coverage is a weak signal for spotting untested areas, never a target; fewer tests with strong assertions beat high coverage with shallow checks.
- One test runner per package: extend the incumbent (Vitest in new TS, Jest where established) — never introduce a second runner without a migration plan.
- E2E harness boots its own servers: let the runner start the app (Playwright `webServer`) and wait on a real readiness URL (`/healthz`) before tests — never a fixed `sleep`. `reuseExistingServer: !CI` keeps local runs fast.
- CI-aware knobs gated on `process.env.CI`: `forbidOnly`, a small retry count, single worker, trace/video on first retry — so CI catches a stray `.only` and a flake leaves a trace, while local stays fast.
- Provide dummy env fallbacks in CI (a throwaway API key, a fake signing secret) so lint/typecheck/build/unit run without real secrets; real credentials gate only the jobs that truly need them.
- Deterministic pure functions (seeded RNG, no wall-clock) are the cheapest thing to unit-test — assert same input produces same output.
