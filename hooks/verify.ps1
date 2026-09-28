# PowerShell twin of verify.sh for agents that run Windows hooks through
# PowerShell (Codex). It reads a Claude Code session transcript; a runtime that
# passes no transcript path, or another format, finds no edit and lets the turn
# end. scripts/lint.py runs both scripts against the same turns.
$ErrorActionPreference = 'Stop'

try {
  $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
} catch {
  exit 0
}
# The second stop in a turn is always allowed, so the agent can answer
# "unverified" instead of being held in a loop.
if ($payload.stop_hook_active -eq $true) { exit 0 }
$transcript = [string]$payload.transcript_path
if (-not $transcript -or -not (Test-Path -LiteralPath $transcript -PathType Leaf)) { exit 0 }

# Line numbers in the session transcript, one JSON record per line. A user
# record without a tool_result is a prompt, so it marks where this turn began.
$turnStart = 0; $lastEdit = 0; $lastCommand = 0; $number = 0
foreach ($line in [System.IO.File]::ReadAllLines($transcript)) {
  $number++
  if ($line -match '"type":"user"' -and $line -notmatch '"tool_result"') { $turnStart = $number }
  if ($line -match '"type":"tool_use"[^}]*"name":"(Edit|Write|MultiEdit|NotebookEdit)"') { $lastEdit = $number }
  if ($line -match '"type":"tool_use"[^}]*"name":"(Bash|PowerShell)"') { $lastCommand = $number }
}

if ($lastEdit -gt $turnStart -and $lastEdit -gt $lastCommand) {
  [Console]::Error.WriteLine('You edited files after your last command. Run the tests or checks of this repository that cover the change before finishing (a snippet you write yourself does not replace them), or say plainly that the change is unverified and why.')
  exit 2
}
exit 0
