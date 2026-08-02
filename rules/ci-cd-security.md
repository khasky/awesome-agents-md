# CI/CD pipeline security

Read this when writing or changing CI workflows, release automation, or anything that runs with repository credentials. Written against GitHub Actions: the trust-boundary rules carry to GitLab CI and Azure Pipelines, the syntax and the variable names do not.

<!-- Distilled from TupleType/awesome-cicd-attacks (poisoned pipeline execution, dependency confusion, runner compromise), GitHub's hardening guide for Actions, zizmor/actionlint rule sets, and Trail of Bits' research on auditing AI-agent workflows in CI. -->

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
- Release artifacts carry provenance: attest at build time (`actions/attest-build-provenance`, sigstore/cosign) and make the consumer verify before install or deploy. An unsigned artifact in a registry is indistinguishable from one an attacker pushed. Rollout strategy and rollback for what those artifacts ship: `rules/deployment.md`.
- Review the lockfile diff on every PR: a new transitive package, a changed integrity hash, or a rewritten registry URL is a supply-chain event, not noise (`rules/dependencies.md`).
- A step that downloads a binary into the runner (a `curl`/`wget` of a release archive, an installer script piped to a shell) pins the exact version *and* verifies a checksum the workflow supplies; an empty checksum fails the step rather than defaulting to trust. Action pinning covers the actions, not the software they fetch.
- Secrets are never printed, echoed, or written to an artifact for debugging; a masked value still leaks through base64, reversal, or a crash dump.
- An AI-agent step (a Claude, Gemini, or Codex action) is an injection sink, not just a tool: issue and PR text, review comments, error logs, and env values all reach its prompt as attacker-controlled input. A prompt with no `${{ }}` in it proves nothing when the payload arrives through an env var or a `gh issue view` the agent runs itself.
- Agent output is untrusted code: never pipe it into `eval`, a shell, or an auto-merged commit. It gets the same review gate as PR-head code before anything executes it with repository credentials.
- Scope what the agent may run: no wildcard tool allowlists, no full-access or auto-approve sandbox flags in CI. Allowlist argument shapes, not bare tool names — `echo $(env)` exfiltrates through an allowed `echo`.
- Sandbox and permission weaknesses do not exploit themselves, they amplify: a permissive agent config turns an otherwise-contained prompt injection into repository write access, so rate the two findings together, not separately.
- The gates that block a merge run in CI, not only in a git hook — hooks are bypassable by design (`rules/git-hooks.md`).
- The pipeline's credentials also sit on developer machines, where none of the above protects them: a laptop that can deploy needs full-disk encryption and a screen lock, and its tokens belong in the OS keychain or a credential helper rather than a plaintext `.npmrc`, `.netrc`, `.env`, or shell history. Prefer a short-lived login (`gh auth login`, `aws sso login`) over a long-lived token pasted into a dotfile — the long-lived one outlives the laptop.
