# PowerShell twin of guard.sh for agents that run Windows hooks through
# PowerShell (Codex): the same blocks and prompts, the same messages,
# exit 2 to block.
# scripts/lint.py runs both scripts against the same commands.
$ErrorActionPreference = 'Stop'

try {
  $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
} catch {
  exit 0
}
$toolInput = $payload.tool_input
if ($toolInput -is [string]) { $toolInput = $toolInput | ConvertFrom-Json }
$command = [string]$toolInput.command
if (-not $command) { exit 0 }
# A newline separates commands the way ; does. Known ceiling: a command
# assembled at run time (a variable, a script file, git commit -F) is not seen.
$command = $command -replace "`r?`n", '; '

function Block([string]$reason) {
  [Console]::Error.WriteLine("Blocked by the awesome-agents-md guard: $reason")
  exit 2
}

function Test-Command([string]$pattern) {
  return [regex]::IsMatch($command, $pattern, 'IgnoreCase')
}

# A segment starts at the line start or after ; & | ( or $( and runs to the
# next separator, so [^;&|]* keeps a flag tied to the git call it belongs to.
$start = '(^|[;&|(]|\$\()\s*'

if ((Test-Command "(^|[^A-Za-z0-9_-])printenv([^A-Za-z0-9_-]|$)|$start(env|set)\s*($|[;&|)])|declare\s+-[A-Za-z0-9]*p|/proc/\S*/environ|(Get-ChildItem|gci|dir|ls|Get-Item|gi)\s+(-Path\s+)?env:(\*|[\s;|]|$)") -and
    -not (Test-Command '[|]\s*(select(-object)?\s+(-expandproperty\s+)?name|%\s*[{]\s*[$]_\.name|cut\s+-d\s*.?=.?\s*-f\s*1)\s*($|[|;&)])')) {
  # A listing reduced to variable names prints no value, and it is how an
  # agent finds a missing variable, so it goes through.
  Block 'printing the environment. Its output enters the transcript with every credential in it: read the one value the task needs, or send both streams to the null device.'
}

# Printing one variable whose name marks a secret leaks it the same way a dump
# does: a bare PowerShell $env:X statement, or echo/printf/Write-* of it.
# Testing that it is set, or passing it to a command, prints nothing.
$secret = '[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)[A-Za-z0-9_]*'
if (Test-Command "$start\`$env:$secret\s*($|[;|)])|(echo|printf|print|Write-Host|Write-Output)\s[^;&|]*\`$(env:)?\{?$secret") {
  Block 'printing a secret variable. Its value enters the transcript: test that it is set ([ -n "$X" ], Test-Path env:X) instead of printing it.'
}

if ((Test-Command 'git\s[^;&|]*commit') -and (Test-Command 'Co-Authored-By|Claude-Session|claude\.ai/code/session')) {
  Block 'an assistant trailer or session link in a commit. Commits carry no assistant trace: drop the trailer and the link.'
}

function Ask([string]$reason) {
  [Console]::Out.WriteLine('{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"awesome-agents-md: ' + $reason + '"}}')
}

# Force-pushing, skipping git hooks and committing are the user's call. Whether
# a prompt asked for one cannot be read from its words in every language, so
# the user confirms the call itself. They come after the blocks, which win.
if (Test-Command 'git\s[^;&|]*push[^;&|]*\s(--force|-[A-Za-z0-9]*f[A-Za-z0-9]*(\s|$)|\+[^\s;&|])') {
  Ask 'this force-pushes and rewrites remote history. Approve only if you asked for it.'
} elseif (Test-Command 'git\s[^;&|]*(--no-verify|core\.hooksPath)') {
  Ask 'this skips git hooks. A failing hook is a check: approve only if you asked to bypass it.'
# Destructive commands only on the targets nothing can restore: a recursive
# delete of the root, home, working directory or .git, uncommitted work, whole
# tables, and a downloaded script run unread. rm -rf build stays ordinary work.
} elseif (Test-Command ($start + '(sudo\s+)?(rm|Remove-Item)\s([^;&|]*\s)?(-[dfirv]*r[dfirv]*|--recursive|-rec[A-Za-z]*)\s([^;&|]*\s)?(/|/\*|~/?|\.{1,2}/?|\*|\.git/?|\$HOME/?)(\s|$|[;&|)])')) {
  Ask 'this recursively deletes the root, the home or working directory, or .git. Approve only if you asked for it.'
} elseif (Test-Command 'git\s[^;&|]*(reset[^;&|]*\s--hard|clean[^;&|]*\s(-[A-Za-z0-9]*f|--force))') {
  Ask 'this discards uncommitted work for good. Approve only if you asked for it.'
} elseif ((Test-Command '(drop\s+(table|database|schema)|truncate\s+(table\s+)?[A-Za-z_])') -or
    ((Test-Command 'delete\s+from\s') -and -not (Test-Command 'delete\s+from\s[^;]*\swhere\s'))) {
  Ask 'this drops or empties a table or database. Approve only if you asked for it.'
} elseif (Test-Command '(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\s[^;&|]*[|]\s*(sudo\s+)?((ba|z|da)?sh|iex|Invoke-Expression|pwsh|powershell)(\s|$|[;&|)])|(iex|Invoke-Expression)\s*[(]\s*(irm|iwr|Invoke-RestMethod|Invoke-WebRequest)|(^|[^A-Za-z0-9_-])(ba|z)?sh\s+(-c\s+)?\S{0,3}(<|[$])[(]\s*(curl|wget)') {
  Ask 'this runs a script downloaded from the network without reading it. Approve only if you trust the source.'
} elseif (Test-Command 'git(\s[^;&|]*)?\scommit(\s|$)') {
  Ask "a commit is the user's call. Approve only if you asked for it."
}

exit 0
