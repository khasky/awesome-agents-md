#!/usr/bin/env bash
# SessionStart: facts about this environment that an agent otherwise learns
# from one failed command each: how the repository's tests run here, and which
# syntax each shell tool takes. Facts only, no rules; silent when there is
# nothing to say. facts.ps1 reports the same runner.
set -euo pipefail
cat > /dev/null || true
facts=()
tests=$(git ls-files 2>/dev/null |
  grep -E '(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*\.(test|spec)\.[a-z]+)$|(^|/)tests?/' |
  head -n 3 | tr '\n' ' ') || true
if [ -n "$tests" ]; then
  runner=''
  case "$tests" in
    *.py*)
      if python -c 'import pytest' >/dev/null 2>&1; then runner='`python -m pytest -q`'
      else runner='`python -m unittest` (pytest is not installed)'; fi ;;
  esac
  if [ -z "$runner" ] && [ -f package.json ] && grep -q '"test"[[:space:]]*:' package.json; then
    runner='`npm test`'
  fi
  if [ -n "$runner" ]; then
    facts+=("This repository's tests (${tests% }) run with $runner from its root.")
  fi
fi
# Claude Code on Windows runs its Bash tool in Git Bash next to a PowerShell
# tool, and a command in the other shell's syntax fails once before it is
# rewritten.
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*)
    facts+=("The Bash tool runs Git Bash (POSIX syntax); PowerShell syntax works only in the PowerShell tool.") ;;
esac
[ ${#facts[@]} -gt 0 ] || exit 0
printf 'awesome-agents-md, facts about this environment: %s\n' "${facts[*]}"
