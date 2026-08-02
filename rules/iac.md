# Infrastructure as code

Read this when writing or reviewing declarative infrastructure — Terraform/OpenTofu, Pulumi, CloudFormation/CDK, or equivalent.

<!-- Distilled from Terraform's state/backend guidance and IaC review practice; cross-checked against production reference implementations. -->

- State is remote with locking from the first commit — local state is an unbackuped database of production on one laptop. The state file holds secrets in plaintext: treat it as a credential (encrypted backend, access-controlled, never committed).
- The plan is the review artifact: apply only a plan someone read. Resource replacements (`-/+`, "forces replacement") are the destructive lines — a replacement of a database, volume, or anything stateful is a destructive operation under the core Boundaries rule, requiring the same explicit confirmation and backup as a `DROP`.
- `destroy`, forced replacement (`apply -replace`), and state surgery (`state rm`/`mv`) fall under the core Boundaries destructive-command rule: never unprompted, always preceded by a state backup.
- Pin provider and module versions exactly; an unpinned module source is a supply-chain dependency with apply-time execution rights (`rules/dependencies.md`).
- Drift is a first-class state: a manual console change makes the next apply revert someone's fix or fail — detect it (scheduled plan in CI), then decide import-or-revert explicitly, never let apply decide.
- One state per environment (separate roots or workspaces); a shared state file turns a staging experiment into a production incident.
- No secret literals in definitions or template files: reference the secret manager or inject via environment-sourced variables — anything inlined lands in state and plan output (core Security).
- Import existing resources before recreating them: a "new" resource colliding with a live name either fails or replaces the running one.
