#!/usr/bin/env bash
# Processes the agent started this turn and left running, at three moments of
# the turn: start (UserPromptSubmit) records every process under the agent;
# after (PostToolUse on a shell call) names those started since that still run;
# stop (Stop) sends the turn back once while any do, so a server, watch or
# browser is stopped or explained instead of left holding memory and ports.
# MCP and language servers predate the turn and never count. Known ceiling: a
# process whose parent already exited is no longer under the agent (Unix
# reparents it, Windows keeps a dead parent id) and is not seen.
set -euo pipefail
mode=${1:-}
# Git Bash cannot see Windows process parents, so on Windows the PowerShell
# twin does the work, and it runs this script everywhere else. A Git Bash
# program started by another one outlives the Windows process it was spawned
# from, so Git Bash's own parent links go along, as Windows pid pairs.
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*)
    AWESOME_AGENTS_MD_MSYS_PARENTS=$(ps -l | awk 'NR > 1 { win[$1] = $4; up[$4] = $2 }
      END { for (w in up) if (up[w] in win) printf "%s:%s ", w, win[up[w]] }')
    export AWESOME_AGENTS_MD_MSYS_PARENTS
    exec powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$(dirname "$0")/survivors.ps1")" "$mode" ;;
esac
payload=$(cat)
# The second stop in a turn is always allowed, so the agent can say why a
# process keeps running instead of being held in a loop.
if [ "$mode" = stop ] && printf '%s' "$payload" | grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

# One line per process: pid, parent, elapsed time, start time (five fields,
# which with the pid name a process across pid reuse), command line.
# Without a terminal procps warns about the screen size on stderr, which would
# reach the agent with the Stop message.
named=$(ps -A -ww -o pid= -o ppid= -o etime= -o lstart= -o args= 2>/dev/null |
  awk -v me="$$" -v mode="$mode" -v tmp="${TMPDIR:-/tmp}" '
    function seconds(t,  days, n, part) {
      days = 0
      if (index(t, "-")) { days = substr(t, 1, index(t, "-") - 1); t = substr(t, index(t, "-") + 1) }
      n = split(t, part, ":")
      return days * 86400 + (n == 3 ? part[1] * 3600 + part[2] * 60 + part[3] : part[1] * 60 + part[2])
    }
    {
      pid = $1; parent[pid] = $2; age[pid] = seconds($3); key[pid] = pid "@" $4 $5 $6 $7 $8
      exe[pid] = $9; sub(/.*\//, "", exe[pid]); sub(/^-/, "", exe[pid])
      line = $9; for (i = 10; i <= NF; i++) line = line " " $i; args[pid] = line
      kids[$2] = kids[$2] " " pid
    }
    END {
      # The agent is the nearest ancestor that is not a shell; root is the
      # process under it this hook runs in, which a hook running beside this
      # one shares the start time of.
      shells = "^(bash|sh|dash|zsh|ksh|fish|cmd|pwsh|powershell)(\\.exe)?$"
      root = me; agent = parent[me]
      while ((agent in exe) && exe[agent] ~ shells) { root = agent; agent = parent[agent] }
      if (!(agent in exe) || agent + 0 <= 1) exit
      state = key[agent]; gsub(/[@:]/, "-", state)
      state = tmp "/awesome-agents-md-survivors-" state ".txt"
      # Every process under the agent, each with the agent child it descends from.
      n = split(kids[agent], queue, " ")
      for (i = 1; i <= n; i++) top[queue[i]] = queue[i]
      for (head = 1; head <= n; head++) {
        m = split(kids[queue[head]], found, " ")
        for (j = 1; j <= m; j++) { queue[++n] = found[j]; top[found[j]] = top[queue[head]] }
      }
      if (mode == "start") {
        print "awesome-agents-md survivors" > state
        for (i = 1; i <= n; i++) print key[queue[i]] > state
        exit
      }
      if ((getline line < state) <= 0 || line != "awesome-agents-md survivors") exit
      while ((getline line < state) > 0) known[line] = 1
      # A tree that began within a second of this hook is a hook running beside it.
      for (i = 1; i <= n; i++) {
        p = queue[i]
        if (!(key[p] in known) && age[top[p]] > age[root] + 1) fresh[p] = 1
      }
      for (i = 1; i <= n; i++) {
        p = queue[i]
        if (!(p in fresh) || (parent[p] in fresh)) continue
        line = args[p]; gsub(/[[:space:]]+/, " ", line)
        if (length(line) > 100) line = substr(line, 1, 100) "..."
        print p " " exe[p] " (" line ")"
      }
    }')
[ -n "$named" ] || exit 0
count=$(printf '%s\n' "$named" | wc -l | tr -d ' ')
list=$(printf '%s\n' "$named" |
  awk 'NR <= 10 { printf "%s%s", (NR > 1 ? "; " : ""), $0 } END { if (NR > 10) printf "; and %d more", NR - 10 }')

if [ "$mode" = stop ]; then
  printf '%s\n' "Processes you started this turn are still running ($count): $list. Stop each one whose job is done, by these process ids and their children only, or say why it keeps running." >&2
  exit 2
fi
note=$(printf '%s' "awesome-agents-md: still running from this turn ($count): $list. Stop the ones whose job is done before you finish." |
  sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$note"
