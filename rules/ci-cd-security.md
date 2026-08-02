# CI/CD pipeline security

Read this when writing or changing CI workflows, release automation, or anything that runs with repository credentials (GitHub Actions, GitLab CI, Azure Pipelines).

<!-- Distilled from TupleType/awesome-cicd-attacks (poisoned pipeline execution, dependency confusion, runner compromise), GitHub's hardening guide for Actions, and zizmor/actionlint rule sets. -->

- Pin every third-party action to a full commit SHA (`uses: owner/action@a1b2c3…`), never a tag or branch — a tag is mutable and repointing it is the documented supply-chain vector. Keep the human-readable version in a trailing comment and let the bot bump both.
- `pull_request_target` and `workflow_run` execute with repository secrets and write scope against the *base* repo: never check out or run PR-head code inside them. A fork PR that genuinely needs a secret goes through a gated `environment` with a required reviewer.
- Least-privilege token: `permissions: contents: read` at workflow top level, escalated per job to exactly what that job writes. Never rely on the default token scope.
- Cloud credentials come from OIDC federation with a short-lived, audience-scoped token — not long-lived `AWS_ACCESS_KEY_ID`/service-account JSON stored as repo secrets.
- `${{ … }}` is expanded by the runner before the shell sees the line, so an expression inside `run:` is code, not a string: pass values through `env:` and reference them as quoted shell variables.
- Treat `github.event.*` as attacker-controlled — PR titles, branch names, issue bodies, and commit messages reach workflows on public repos and are the standard script-injection source.
- Untrusted and trusted jobs never share a cache key or an artifact: a fork-writable cache restored into a release job, or an artifact uploaded by a PR job and consumed by a signing job, is code execution across the trust boundary.
- Self-hosted runners never serve public-fork PRs, and are ephemeral (one job per instance) — a persistent runner leaks the previous job's state to the next.
- Lint the workflow YAML itself in CI (`zizmor`, `actionlint`) — these files are the least-reviewed executable code in most repos.
- `GITHUB_ENV` and `GITHUB_OUTPUT` are files one step writes and the next step trusts: an untrusted value containing a newline injects a variable into the following step. Route untrusted content through neither, or write it with a random heredoc delimiter.
- Reusable workflows and composite actions run with the caller's secrets and token — pin them by SHA like any other action, and treat one owned by another org as third-party code holding write access to this repo.
- Release artifacts carry provenance: attest at build time (`actions/attest-build-provenance`, sigstore/cosign) and make the consumer verify before install or deploy. An unsigned artifact in a registry is indistinguishable from one an attacker pushed.
- Review the lockfile diff on every PR: a new transitive package, a changed integrity hash, or a rewritten registry URL is a supply-chain event, not noise (`rules/dependencies.md`).
- Secrets are never printed, echoed, or written to an artifact for debugging; a masked value still leaks through base64, reversal, or a crash dump.
- The gates that block a merge run in CI, not only in a git hook — hooks are bypassable by design (`rules/git-hooks.md`).
