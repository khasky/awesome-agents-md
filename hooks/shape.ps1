# PowerShell twin of shape.sh for agents that run Windows hooks through
# PowerShell (Codex): the same guidance for the same files, as the same JSON.
$ErrorActionPreference = 'Stop'

try {
  $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
} catch {
  exit 0
}
$file = [string]$payload.tool_response.filePath
if (-not $file) { $file = [string]$payload.tool_input.file_path }
if ($file -notmatch '\.(py|js|mjs|cjs|ts|tsx|jsx|go|rs|java|rb|php|cs|cpp|c|kt|swift)$') { exit 0 }
$name = Split-Path -Leaf $file
if ($name -match '^test_|_test\.|\.test\.|\.spec\.') { exit 0 }
$dir = Split-Path -Parent $file
$tests = @()
try {
  $tests = @(git -C $dir ls-files 2>$null | Where-Object {
      $_ -match '(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*\.(test|spec)\.[a-z]+)$|(^|/)tests?/' } |
    Select-Object -First 3)
} catch { $tests = @() }

if ([string]$payload.tool_response.type -eq 'create') {
  $lines = 0
  if (Test-Path -LiteralPath $file -PathType Leaf) {
    $lines = @([System.IO.File]::ReadAllLines($file) | Where-Object { $_.Trim() }).Count
  }
  $note = "You created $name ($lines lines). An open request stays under 60 lines unless it names more: delete what it did not name (options, modes, tiers, checks, CLI parsing, persistence, docstrings), keep input validation at trust boundaries. Prove it with one shell call on input given in the command itself, no temporary files; fix only what that run shows broken, then answer."
} elseif ($tests.Count -gt 0) {
  $top = (git -C $dir rev-parse --show-toplevel 2>$null)
  if (-not $top) { $top = $dir }
  $runner = ''
  if (($tests -join ' ') -match '\.py') {
    # Windows PowerShell turns a native command's stderr into a terminating
    # error under 'Stop'; the probe's ImportError is an answer, not a failure.
    $ErrorActionPreference = 'Continue'
    & python -c 'import pytest' 2>$null | Out-Null
    $hasPytest = $LASTEXITCODE -eq 0
    $ErrorActionPreference = 'Stop'
    $runner = if ($hasPytest) { 'python -m pytest -q' } else { 'python -m unittest' }
  }
  $package = Join-Path $top 'package.json'
  if (-not $runner -and (Test-Path -LiteralPath $package) -and
      ([System.IO.File]::ReadAllText($package) -match '"test"\s*:')) { $runner = 'npm test' }
  $how = if ($runner) { " with ``$runner`` from the repository root" } else { '' }
  $note = "This repository has tests ($($tests -join ' ')). After your last code edit, prove it by running them$how; a snippet does not replace them."
} else {
  exit 0
}
$out = @{ hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = $note } } |
  ConvertTo-Json -Compress
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::Out.Write($out + "`n")
