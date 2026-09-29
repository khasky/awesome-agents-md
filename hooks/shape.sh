#!/usr/bin/env bash
# PostToolUse on Write and Edit: one line of guidance at the moment it applies,
# so the agent acts on it in the flow of the work instead of being sent back
# after a finished answer. A source file just created: keep an open request
# small and prove it with one run. A code file edited in a repository with
# tests: prove it with them, named with a command that runs here.
set -euo pipefail
payload=$(cat)
file=$(printf '%s' "$payload" | grep -oE '"(filePath|file_path)"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' | head -n 1 |
  sed -E 's/^"(filePath|file_path)"[[:space:]]*:[[:space:]]*"//; s/"$//; s/\\\\/\//g') || true
case "$file" in
  *.py|*.js|*.mjs|*.cjs|*.ts|*.tsx|*.jsx|*.go|*.rs|*.java|*.rb|*.php|*.cs|*.cpp|*.c|*.kt|*.swift) ;;
  *) exit 0 ;;
esac
name=${file##*/}
case "$name" in test_*|*_test.*|*.test.*|*.spec.*) exit 0 ;; esac
dir=${file%/*}
tests=$(git -C "$dir" ls-files 2>/dev/null |
  grep -E '(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*\.(test|spec)\.[a-z]+)$|(^|/)tests?/' |
  head -n 3 | tr '\n' ' ') || true
if printf '%s' "$payload" | grep -qE '"type"[[:space:]]*:[[:space:]]*"create"'; then
  lines=0
  [ -f "$file" ] && lines=$(grep -c '[^[:space:]]' "$file" || true)
  note="You created $name ($lines lines). An open request stays under 60 lines unless it names more: delete what it did not name (options, modes, tiers, checks, CLI parsing, persistence, docstrings), keep input validation at trust boundaries. Prove it with one shell call on input given in the command itself, no temporary files; fix only what that run shows broken, then answer."
elif [ -n "$tests" ]; then
  top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$dir")
  runner=''
  case "$tests" in
    *.py*)
      if python -c 'import pytest' >/dev/null 2>&1; then runner='python -m pytest -q'; else runner='python -m unittest'; fi ;;
  esac
  if [ -z "$runner" ] && [ -f "$top/package.json" ] && grep -q '"test"[[:space:]]*:' "$top/package.json"; then
    runner='npm test'
  fi
  how=${runner:+ with \`$runner\` from the repository root}
  note="This repository has tests (${tests% }). After your last code edit, prove it by running them$how; a snippet does not replace them."
else
  exit 0
fi
note=$(printf '%s' "$note" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$note"
