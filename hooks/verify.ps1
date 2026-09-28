# PowerShell twin of verify.sh for agents that run Windows hooks through
# PowerShell (Codex): the same three checks, the same messages. It reads a
# Claude Code session transcript; a runtime that passes no transcript path, or
# another format, finds nothing and lets the turn end. scripts/lint.py runs both
# scripts against the same turns.
$ErrorActionPreference = 'Stop'
$AnswerWordLimit = 35

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
$turnStart = 0; $turnStartLine = ''; $lastEdit = 0; $lastCommand = 0; $lastText = 0; $lastTextLine = ''; $number = 0
foreach ($line in [System.IO.File]::ReadAllLines($transcript)) {
  $number++
  if ($line -match '"type":"user"' -and $line -notmatch '"tool_result"') { $turnStart = $number; $turnStartLine = $line }
  if ($line -match '"type":"tool_use"[^}]*"name":"(Edit|Write|MultiEdit|NotebookEdit)"') { $lastEdit = $number }
  if ($line -match '"type":"tool_use"[^}]*"name":"(Bash|PowerShell)"') { $lastCommand = $number }
  if ($line -match '"type":"text"' -and $line -match '"role":"assistant"') { $lastText = $number; $lastTextLine = $line }
}

if ($lastText -gt $turnStart -and $lastTextLine -match '(?i)co-authored-by|claude-session|claude\.ai/code/session') {
  [Console]::Error.WriteLine('Your reply carries an assistant trace (a Co-Authored-By or session trailer). Commit messages, proposed or made, carry none: give the reply again without it.')
  exit 2
}

if ($lastEdit -gt $turnStart -and $lastEdit -gt $lastCommand) {
  [Console]::Error.WriteLine('You edited files after your last command. Run the tests or checks of this repository that cover the change before finishing (a snippet you write yourself does not replace them), or say plainly that the change is unverified and why.')
  exit 2
}

# A source file created in this turn gets one trimming pass: an open request is
# where agents build tiers, modes and options nobody named. Test files and
# non-code files are left alone.
$lines = [System.IO.File]::ReadAllLines($transcript)
foreach ($line in $lines[$turnStart..($lines.Length - 1)]) {
  foreach ($hit in [regex]::Matches($line, 'File created successfully at: [^"(]*\.(py|js|mjs|cjs|ts|tsx|jsx|go|rs|java|rb|php|cs|cpp|c|kt|swift)([^A-Za-z0-9]|$)')) {
    if ($hit.Value -notmatch '(?i)(^|[\\/])(test_[^\\/]*|tests?[\\/])|[._-](test|spec)\.') {
      [Console]::Error.WriteLine('Before finishing, re-read the source file you created and delete what the request did not name: extra options, modes, tiers, checks, CLI parsing, persistence, docstrings. Keep input validation at trust boundaries, error handling that prevents data loss and one runnable check. Run it once more, then answer in at most three short lines.')
      exit 2
    }
  }
}

# The answer itself stays short: words outside code blocks, before the commit
# proposal and without the canary line. A prompt asking for an explanation lifts
# the limit, since the length is then what was asked for.
if ($lastText -le $turnStart) { exit 0 }
$explain = '(?i)explain|why|walk me through|in detail|объясн|почему|подробн|\\u043e\\u0431\\u044a\\u044f\\u0441\\u043d|\\u043f\\u043e\\u0447\\u0435\\u043c\\u0443|\\u043f\\u043e\\u0434\\u0440\\u043e\\u0431\\u043d'
if ($turnStartLine -match $explain) { exit 0 }
try {
  $record = $lastTextLine | ConvertFrom-Json
} catch {
  exit 0
}
$text = (@($record.message.content) | Where-Object { $_.type -eq 'text' } | ForEach-Object { $_.text }) -join "`n"
$words = 0; $fence = $false
foreach ($line in ($text -split "`r?`n")) {
  $lower = $line.ToLowerInvariant()
  if ($lower.Length -lt 60 -and $lower -match '^[^a-z0-9]*((recommended|suggested|proposed) )?commit( message)?([^a-z0-9][^.]*)?$') { break }
  if ($line -match '^\s*```') { $fence = -not $fence; continue }
  if ($fence -or $line -match 'awesome-agents-md') { continue }
  $words += @($line -split '\s+' | Where-Object { $_ }).Count
}
if ($words -gt $AnswerWordLimit) {
  [Console]::Error.WriteLine("Your answer is $words words. Give it again in at most three short lines (what changed or happened, the evidence, what is unverified or the options); keep the commit proposal, code and warnings as they are.")
  exit 2
}
exit 0
