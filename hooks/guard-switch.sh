#!/usr/bin/env bash
# UserPromptSubmit hook behind /awesome-agents-md:guard: turns the guard's
# push and recursive-delete prompts off or on. It answers the command itself
# and blocks the prompt, so no model turn runs and the agent never writes the
# switch file. Any other prompt passes untouched, a bare /guard included: that
# name may belong to another plugin.
set -euo pipefail

payload=$(cat)
prompt=$(printf '%s' "$payload" |
  grep -oE '"prompt"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' |
  head -n 1 |
  sed -E 's/^"prompt"[[:space:]]*:[[:space:]]*"//; s/"$//; s/\\[nrt]/ /g') || true

# Typed as text the command arrives as is; an interactive session can wrap it
# as <command-name>/awesome-agents-md:guard</command-name><command-args>push off</command-args>.
envelope='<command-name>[[:space:]]*/awesome-agents-md:guard[[:space:]]*</command-name>'
envelope_args='<command-args>([^<]*)</command-args>'
literal='^[[:space:]]*/awesome-agents-md:guard([[:space:]]+(.*))?$'
args=''
if [[ $prompt =~ $envelope ]]; then
  if [[ $prompt =~ $envelope_args ]]; then
    args=${BASH_REMATCH[1]}
  fi
elif [[ $prompt =~ $literal ]]; then
  args=${BASH_REMATCH[2]}
else
  exit 0
fi

switch_file="$HOME/.awesome-agents-md/guard"
state() {
  if grep -qxF "$1=off" "$switch_file" 2>/dev/null; then echo off; else echo on; fi
}

label() {
  if [ "$1" = push ]; then echo push; else echo recursive-delete; fi
}
# One line per switch: its state and the command that flips it.
line() {
  local now flip
  now=$(state "$1")
  if [ "$now" = on ]; then flip=off; else flip=on; fi
  printf '%s prompt: %s (/awesome-agents-md:guard %s %s)' "$(label "$1")" "$now" "$1" "$flip"
}

read -r -a words <<< "$(printf '%s' "$args" | tr '[:upper:]' '[:lower:]')"
set -- ${words[@]+"${words[@]}"}
title='awesome-agents-md guard:'
if [ $# -eq 2 ] && [[ $1 =~ ^(push|delete)$ ]] && [[ $2 =~ ^(on|off)$ ]]; then
  if [ "$(state "$1")" = "$2" ]; then
    title="$title $(label "$1") prompt is already $2."
  else
    mkdir -p "${switch_file%/*}"
    others=$(grep -vxF "$1=off" "$switch_file" 2>/dev/null) || true
    {
      if [ -n "$others" ]; then printf '%s\n' "$others"; fi
      if [ "$2" = off ]; then printf '%s=off\n' "$1"; fi
    } > "$switch_file.tmp"
    mv -f "$switch_file.tmp" "$switch_file"
    title="$title $(label "$1") prompt turned $2."
  fi
elif [ $# -ne 0 ]; then
  title="$title usage: /awesome-agents-md:guard [push|delete] [on|off]."
fi

printf '{"decision":"block","reason":"%s\\n%s\\n%s"}\n' "$title" "$(line push)" "$(line delete)"
exit 0
