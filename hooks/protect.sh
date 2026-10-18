#!/usr/bin/env bash
# PreToolUse on file edits: an edit to an existing check configuration (lint,
# format, type check, test runner, git hooks, CI) or to the files that
# constrain the agent (AGENTS.md, CLAUDE.md, agent settings, .gitignore) is
# the user's call, so the user confirms it. A failing check made to pass by
# loosening its config reports done on work nobody did. Creating such a file
# is ordinary setup work and goes through.
set -euo pipefail
payload=$(cat)

# Claude Code names the file in file_path; Codex sends apply_patch, whose patch
# names each file on an "*** Update File:" line.
files=$({ printf '%s' "$payload" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' |
    sed -E 's/^"file_path"[[:space:]]*:[[:space:]]*"//; s/"$//; s/\\\\/\//g'
  printf '%s' "$payload" | grep -oE '\*\*\* (Update|Delete) File: [^"\\]+' |
    sed -E 's/^\*\*\* (Update|Delete) File: //'; } || true)
[ -n "$files" ] || exit 0

while IFS= read -r file; do
  [ -n "$file" ] && [ -f "$file" ] || continue
  name=${file##*/}
  case "$file" in
    */.github/workflows/*|.github/workflows/*|*/.husky/*|.husky/*|*/.claude/settings*.json|.claude/settings*.json) hit=1 ;;
    *)
      case "$name" in
        AGENTS.md|CLAUDE.md|.gitignore|.eslintrc*|eslint.config.*|.prettierrc*|prettier.config.*|biome.json|biome.jsonc|\
        .stylelintrc*|stylelint.config.*|ruff.toml|.ruff.toml|.flake8|.pylintrc|mypy.ini|.mypy.ini|pytest.ini|tox.ini|\
        .golangci.yml|.golangci.yaml|.rubocop.yml|.pre-commit-config.yaml|lefthook.yml|.lefthook.yml|.gitlab-ci.yml|\
        .markdownlint*|.commitlintrc*|commitlint.config.*) hit=1 ;;
        *) hit=0 ;;
      esac ;;
  esac
  if [ "$hit" = 1 ]; then
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"awesome-agents-md: this edits %s, a check configuration or a file that constrains the agent. Approve only if you asked for this change."}}\n' "$name"
    exit 0
  fi
done <<< "$files"
exit 0
