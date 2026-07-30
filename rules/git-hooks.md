# Git hooks and pre-commit gates

Read this when setting up or changing pre-commit/pre-push automation (husky, lint-staged, pre-commit, lefthook).

<!-- Distilled from the husky and lint-staged docs and pre-commit-hook practice; cross-checked against production reference implementations. -->

- Pre-commit runs on staged files only (lint-staged), not the whole repo — fast enough that nobody is tempted by `--no-verify`. Whole-repo lint/typecheck/test belongs in CI, not the commit hook.
- Auto-install hooks on dependency install (`prepare: husky`) so every clone gets them without a manual step.
- lint-staged runs the formatter and linter with zero tolerance on the staged set (`eslint --max-warnings 0`, `prettier --write`/`--check`); auto-fixable issues fix-and-restage, non-fixable ones block the commit.
- Keep hooks deterministic and side-effect-free — no network calls, no writes outside the staged files; a flaky hook trains developers to bypass it.
- CI re-runs the same gates: hooks are a fast local shortcut, never the source of truth, since `--no-verify` and non-husky clients skip them.
- Never weaken a shared hook to fix a local-only problem (core Boundaries rule) — fix your environment instead.
