# Deployment and release

Read this when shipping a change to a running environment: rollout strategy, rollbacks, feature flags, migration ordering.

<!-- Distilled from continuous-delivery practice (deploy/release separation, progressive delivery), the expand/contract pattern, and feature-flag lifecycle guidance; cross-checked against production reference implementations. -->

- Deploy and release are separate events: deploying puts code in production dark; releasing turns it on (flag, router weight). Coupling them makes every rollback a redeploy under incident pressure.
- Every deploy has a tested rollback path before it starts: the previous artifact still deployable, migrations compatible one version back. A change that can't roll back (data rewrite, destructive migration) is declared as such and ships alone, never bundled.
- Expand/contract ordering is a deploy contract, not just a schema pattern: ship code tolerating both shapes → expand/migrate → switch reads and writes → contract only after every consumer is off the old shape. It applies to API fields, event schemas, and config keys the same as columns (`rules/database.md`, `rules/messaging.md`).
- A rolling deploy runs old and new code side by side against the same database and queues — every change must be compatible with its immediate predecessor, or the deploy needs a declared maintenance window.
- Progressive rollout for risky changes: a canary or percentage stage with promote/abort metrics (error rate, latency vs baseline) watched for a stated bake time — an unwatched canary is just a slow full rollout.
- Feature flags are code with a lifecycle: each flag records an owner, a default (off for releases), and a removal condition at creation. A flag that outlives its rollout is a permanent untested branch — two code paths, one of them dark.
- A kill switch is not a release flag: it is permanent, exercised regularly, and fails safe (flag service down → a per-flag decision of last-known or safe default); a release flag is temporary by definition.
- Flag evaluation is consistent within one request/session — a mid-request flip splits a user across both code paths.
- Migrations deploy separately from, and before, the code that needs them — a step that both migrates and serves couples schema state to instance count mid-rollout (`rules/containers.md`).
- Releases are tagged and their changelog/artifacts produced by CI, not by hand (`rules/ci-cd-security.md`).
