#!/usr/bin/env bash
# PreToolUse guard for shell tools: blocks the commands the core Boundaries,
# Security and Commits rules forbid outright, so they no longer depend on the
# model remembering them. Exit 2 blocks the call and hands stderr to the agent
# as the reason.
set -euo pipefail

payload=$(cat)

# Only git and the OS shell are assumed, so the command field is pulled out with
# a regex instead of a JSON parser. JSON escapes stay in the text; an escaped
# newline becomes a command separator. Known ceiling: a command assembled at run
# time (a variable, a script file, git commit -F) is not seen.
command=$(printf '%s' "$payload" |
  grep -oE '"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' |
  head -n 1 |
  sed -E 's/^"command"[[:space:]]*:[[:space:]]*"//; s/"$//; s/\\n/; /g') || true
[ -n "$command" ] || exit 0

block() {
  printf 'Blocked by the awesome-agents-md guard: %s\n' "$1" >&2
  exit 2
}

matches() {
  printf '%s' "$command" | grep -qEi -- "$1"
}

# A segment starts at the line start or after ; & | ( or $( and runs to the
# next separator, so [^;&|]* keeps a flag tied to the git call it belongs to.
start='(^|[;&|(]|\$\()[[:space:]]*'

if matches 'git[[:space:]][^;&|]*(--no-verify|core\.hooksPath)'; then
  block 'skipping git hooks. A failing hook is a check: fix what it reports, or name the hook, say why you believe it is wrong, and stop.'
fi

if matches "git[[:space:]][^;&|]*push[^;&|]*[[:space:]](--force|-[[:alnum:]]*f[[:alnum:]]*([[:space:]]|$)|\+[^[:space:];&|])"; then
  block 'force-push. Rewriting remote history is the user'"'"'s call: report the rejected push, the repository state and the options, and stop.'
fi

if matches "(^|[^[:alnum:]_-])printenv([^[:alnum:]_-]|$)|${start}(env|set)[[:space:]]*($|[;&|)])|declare[[:space:]]+-[[:alnum:]]*p|/proc/[^[:space:]]*/environ|(Get-ChildItem|gci|dir|ls|Get-Item|gi)[[:space:]]+(-Path[[:space:]]+)?env:(\*|[[:space:];|]|$)"; then
  block 'printing the environment. Its output enters the transcript with every credential in it: read the one value the task needs, or send both streams to the null device.'
fi

if matches 'git[[:space:]][^;&|]*commit' && matches 'Co-Authored-By|Claude-Session|claude\.ai/code/session'; then
  block 'an assistant trailer or session link in a commit. Commits carry no assistant trace: drop the trailer and the link.'
fi

exit 0
