#!/usr/bin/env bash
# PreToolUse guard for shell tools: blocks the commands the core Boundaries,
# Security and Commits rules forbid outright, and asks the user to confirm the
# ones that are only theirs to allow, so neither depends on the model
# remembering them. Exit 2 blocks the call and hands stderr to the agent as the
# reason.
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

if matches "(^|[^[:alnum:]_-])printenv([^[:alnum:]_-]|$)|${start}(env|set)[[:space:]]*($|[;&|)])|declare[[:space:]]+-[[:alnum:]]*p|/proc/[^[:space:]]*/environ|(Get-ChildItem|gci|dir|ls|Get-Item|gi)[[:space:]]+(-Path[[:space:]]+)?env:(\*|[[:space:];|]|$)" &&
  ! matches '[|][[:space:]]*(select(-object)?[[:space:]]+(-expandproperty[[:space:]]+)?name|%[[:space:]]*[{][[:space:]]*[$]_\.name|cut[[:space:]]+-d[[:space:]]*.?=.?[[:space:]]*-f[[:space:]]*1)[[:space:]]*($|[|;&)])'; then
  # A listing reduced to variable names prints no value, and it is how an
  # agent finds a missing variable, so it goes through.
  block 'printing the environment. Its output enters the transcript with every credential in it: read the one value the task needs, or send both streams to the null device.'
fi

# Printing one variable whose name marks a secret leaks it the same way a dump
# does: a bare PowerShell $env:X statement, or echo/printf/Write-* of it.
# Testing that it is set, or passing it to a command, prints nothing.
secret='[[:alnum:]_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)[[:alnum:]_]*'
if matches "${start}\\\$env:${secret}[[:space:]]*(\$|[;|)])|(echo|printf|print|Write-Host|Write-Output)[[:space:]][^;&|]*\\\$(env:)?\\{?${secret}"; then
  block 'printing a secret variable. Its value enters the transcript: test that it is set ([ -n "$X" ], Test-Path env:X) instead of printing it.'
fi

if matches 'git[[:space:]][^;&|]*commit' && matches 'Co-Authored-By|Claude-Session|claude\.ai/code/session'; then
  block 'an assistant trailer or session link in a commit. Commits carry no assistant trace: drop the trailer and the link.'
fi

ask() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"awesome-agents-md: %s"}}\n' "$1"
}

# Force-pushing, skipping git hooks and committing are the user's call. Whether
# a prompt asked for one cannot be read from its words in every language, so
# the user confirms the call itself. They come after the blocks, which win.
if matches "git[[:space:]][^;&|]*push[^;&|]*[[:space:]](--force|-[[:alnum:]]*f[[:alnum:]]*([[:space:]]|$)|\+[^[:space:];&|])"; then
  ask 'this force-pushes and rewrites remote history. Approve only if you asked for it.'
elif matches 'git[[:space:]][^;&|]*(--no-verify|core\.hooksPath)'; then
  ask 'this skips git hooks. A failing hook is a check: approve only if you asked to bypass it.'
# Destructive commands only on the targets nothing can restore: a recursive
# delete of the root, home, working directory or .git, uncommitted work, whole
# tables, and a downloaded script run unread. rm -rf build stays ordinary work.
elif matches "${start}"'(sudo[[:space:]]+)?(rm|Remove-Item)[[:space:]]([^;&|]*[[:space:]])?(-[dfirv]*r[dfirv]*|--recursive|-rec[[:alpha:]]*)[[:space:]]([^;&|]*[[:space:]])?(/|/\*|~/?|\.{1,2}/?|\*|\.git/?|\$HOME/?)([[:space:]]|$|[;&|)])'; then
  ask 'this recursively deletes the root, the home or working directory, or .git. Approve only if you asked for it.'
elif matches 'git[[:space:]][^;&|]*(reset[^;&|]*[[:space:]]--hard|clean[^;&|]*[[:space:]](-[[:alnum:]]*f|--force))'; then
  ask 'this discards uncommitted work for good. Approve only if you asked for it.'
elif matches '(drop[[:space:]]+(table|database|schema)|truncate[[:space:]]+(table[[:space:]]+)?[[:alpha:]_])' ||
  { matches 'delete[[:space:]]+from[[:space:]]' && ! matches 'delete[[:space:]]+from[[:space:]][^;]*[[:space:]]where[[:space:]]'; }; then
  ask 'this drops or empties a table or database. Approve only if you asked for it.'
elif matches '(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)[[:space:]][^;&|]*[|][[:space:]]*(sudo[[:space:]]+)?((ba|z|da)?sh|iex|Invoke-Expression|pwsh|powershell)([[:space:]]|$|[;&|)])|(iex|Invoke-Expression)[[:space:]]*[(][[:space:]]*(irm|iwr|Invoke-RestMethod|Invoke-WebRequest)|(^|[^[:alnum:]_-])(ba|z)?sh[[:space:]]+(-c[[:space:]]+)?[^[:space:]]{0,3}(<|[$])[(][[:space:]]*(curl|wget)'; then
  ask 'this runs a script downloaded from the network without reading it. Approve only if you trust the source.'
elif matches 'git([[:space:]][^;&|]*)?[[:space:]]commit([[:space:]]|$)'; then
  ask 'a commit is the user'"'"'s call. Approve only if you asked for it.'
fi

exit 0
