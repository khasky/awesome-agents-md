# Git hooks and pre-commit gates

Read this when setting up or changing pre-commit/pre-push automation. Written against husky + lint-staged in a JS/TS repo: the gate rules carry to `pre-commit` and lefthook, the commands do not.

<!-- Distilled from the husky and lint-staged docs and pre-commit-hook practice; cross-checked against production reference implementations. -->

- Pre-commit runs on staged files only (lint-staged), not the whole repo — fast enough that nobody is tempted by `--no-verify`. Whole-repo lint/typecheck/test belongs in CI, not the commit hook.
- Auto-install hooks on dependency install (`prepare: husky`) so every clone gets them without a manual step.
- lint-staged runs the formatter and linter with zero tolerance on the staged set (`eslint --max-warnings 0`, `prettier --write`/`--check`); auto-fixable issues fix-and-restage, non-fixable ones block the commit.
- A `commit-msg` hook validates the message against the repo's convention (`commitlint` for Conventional Commits) — the core Commits rule states the format, and the hook is where it stops being advisory.
- Secret scanning runs in the hook as well as in CI (`gitleaks protect --staged`, `detect-secrets`): once a key reaches a pushed commit the remedy is rotation, not a revert (core Security rule).
- Give the hook a time budget and hold it — a pre-commit over a couple of seconds trains everyone to reach for `--no-verify`. Anything slower moves to pre-push or CI.
- Keep hooks deterministic and side-effect-free — no network calls, no writes outside the staged files; a flaky hook trains developers to bypass it.
- CI re-runs the same gates: hooks are a fast local shortcut, never the source of truth, since `--no-verify` and non-husky clients skip them.
- Never weaken a shared hook to fix a local-only problem (core Boundaries rule) — fix your environment instead.
