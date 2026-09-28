# PowerShell twin of guard.sh for agents that run Windows hooks through
# PowerShell (Codex): the same four blocks, the same messages, exit 2 to block.
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

if (Test-Command 'git\s[^;&|]*(--no-verify|core\.hooksPath)') {
  Block 'skipping git hooks. A failing hook is a check: fix what it reports, or name the hook, say why you believe it is wrong, and stop.'
}

if (Test-Command 'git\s[^;&|]*push[^;&|]*\s(--force|-[A-Za-z0-9]*f[A-Za-z0-9]*(\s|$)|\+[^\s;&|])') {
  Block "force-push. Rewriting remote history is the user's call: report the rejected push, the repository state and the options, and stop."
}

if (Test-Command "(^|[^A-Za-z0-9_-])printenv([^A-Za-z0-9_-]|$)|$start(env|set)\s*($|[;&|)])|declare\s+-[A-Za-z0-9]*p|/proc/\S*/environ|(Get-ChildItem|gci|dir|ls|Get-Item|gi)\s+(-Path\s+)?env:(\*|[\s;|]|$)") {
  Block 'printing the environment. Its output enters the transcript with every credential in it: read the one value the task needs, or send both streams to the null device.'
}

if ((Test-Command 'git\s[^;&|]*commit') -and (Test-Command 'Co-Authored-By|Claude-Session|claude\.ai/code/session')) {
  Block 'an assistant trailer or session link in a commit. Commits carry no assistant trace: drop the trailer and the link.'
}

exit 0
