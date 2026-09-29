#!/usr/bin/env bash
# Stop hook, three checks on the turn that is ending, the first that fails
# sending the agent back once. Its final reply carries an assistant trace (a
# Co-Authored-By or session trailer in a proposed commit message, which the
# shell guard never sees); it edited files and ran no command after its last
# edit; or its answer runs past the word limit. Exit 2 keeps the turn going and
# hands stderr to the agent.
set -euo pipefail

# An answer past ANSWER_WORD_TRIGGER words is sent back to be cut to
# ANSWER_WORD_TARGET. Below the trigger a rewrite costs a whole turn and, on the
# benchmark's larger models, came back about as long.
ANSWER_WORD_TRIGGER=60
ANSWER_WORD_TARGET=35

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
# Only an edit to code needs a check after it; a changelog or a note does not.
last_edit=$(last_line '"type":"tool_use"[^}]*"name":"(Edit|Write|MultiEdit|NotebookEdit)"[^}]*"file_path":"[^"]*\.(py|js|mjs|cjs|ts|tsx|jsx|go|rs|java|rb|php|cs|cpp|c|h|kt|swift|sh|ps1|sql)"')
last_command=$(last_line '"type":"tool_use"[^}]*"name":"(Bash|PowerShell)"')
# Claude Code writes the record's own "type" after its message, so the reply
# text is found by the message's role and block type, in either order.
last_text=$({ grep -n '"type":"text"' "$transcript" || true; } |
  { grep '"role":"assistant"' || true; } | tail -n 1 | cut -d: -f1)

if [ "${last_text:-0}" -gt "${turn_start:-0}" ] &&
  sed -n "${last_text}p" "$transcript" | grep -qiE 'co-authored-by|claude-session|claude\.ai/code/session'; then
  printf '%s\n' 'Your reply carries an assistant trace (a Co-Authored-By or session trailer). Commit messages, proposed or made, carry none: give the reply again without it.' >&2
  exit 2
fi

if [ "${last_edit:-0}" -gt "${turn_start:-0}" ] && [ "${last_edit:-0}" -gt "${last_command:-0}" ]; then
  printf '%s\n' 'You edited files after your last command. Run the tests or checks of this repository that cover the change before finishing (a snippet you write yourself does not replace them), or say plainly that the change is unverified and why.' >&2
  exit 2
fi


# The answer itself stays short: words outside code blocks, before the commit
# proposal and without the canary line. A prompt asking for an explanation lifts
# the limit, since the length is then what was asked for.
[ "${last_text:-0}" -gt "${turn_start:-0}" ] || exit 0
if sed -n "${turn_start:-1}p" "$transcript" |
  grep -qiE 'explain|why|walk me through|in detail|объясн|почему|подробн|\\u043e\\u0431\\u044a\\u044f\\u0441\\u043d|\\u043f\\u043e\\u0447\\u0435\\u043c\\u0443|\\u043f\\u043e\\u0434\\u0440\\u043e\\u0431\\u043d'; then
  exit 0
fi
words=$(sed -n "${last_text}p" "$transcript" |
  grep -oE '"text":"([^"\\]|\\.)*"' |
  sed -E 's/^"text":"//; s/"$//; s/\\n/\n/g; s/\\"/"/g' |
  awk '{ line = tolower($0) }
    line ~ /^[^a-z0-9]*((recommended|suggested|proposed) )?commit( message)?([^a-z0-9][^.]*)?$/ && length(line) < 60 { exit }
    /^[[:space:]]*```/ { fence = !fence; next }
    fence || /awesome-agents-md/ { next }
    { words += NF }
    END { print words + 0 }')
if [ "${words:-0}" -gt "$ANSWER_WORD_TRIGGER" ]; then
  printf 'Your answer is %s words. Give it again in at most %s words: what changed or happened, the evidence, what is unverified or the options; keep the commit proposal, code and warnings as they are.\n' "$words" "$ANSWER_WORD_TARGET" >&2
  exit 2
fi
exit 0
