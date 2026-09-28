#!/usr/bin/env bash
# Stop hook: when the agent edited files in this turn and ran no command after
# its last edit, it is sent back once to run the check that proves the change
# or to say the change is unverified. Exit 2 keeps the turn going and hands
# stderr to the agent.
set -euo pipefail

payload=$(cat)

# The second stop in a turn is always allowed, so the agent can answer
# "unverified" instead of being held in a loop.
if printf '%s' "$payload" | grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

transcript=$(printf '%s' "$payload" |
  grep -oE '"transcript_path"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' |
  head -n 1 |
  sed -E 's/^"transcript_path"[[:space:]]*:[[:space:]]*"//; s/"$//; s/\\\\/\//g') || true
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

# Line numbers in the session transcript, one JSON record per line. A user
# record without a tool_result is a prompt, so it marks where this turn began.
last_line() {
  { grep -nE "$1" "$transcript" || true; } | { grep -vE "${2:-^$}" || true; } |
    tail -n 1 | cut -d: -f1
}
turn_start=$(last_line '"type":"user"' '"tool_result"')
last_edit=$(last_line '"type":"tool_use"[^}]*"name":"(Edit|Write|MultiEdit|NotebookEdit)"')
last_command=$(last_line '"type":"tool_use"[^}]*"name":"(Bash|PowerShell)"')

if [ "${last_edit:-0}" -gt "${turn_start:-0}" ] && [ "${last_edit:-0}" -gt "${last_command:-0}" ]; then
  printf '%s\n' 'You edited files after your last command. Run the tests or checks of this repository that cover the change before finishing (a snippet you write yourself does not replace them), or say plainly that the change is unverified and why.' >&2
  exit 2
fi
exit 0
