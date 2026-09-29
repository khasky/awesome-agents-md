# PowerShell twin of facts.sh for agents that run Windows hooks through
# PowerShell (Codex): the same test-runner fact. The shell-syntax fact is about
# Claude Code's Bash tool, which this runtime does not have.
$ErrorActionPreference = 'Stop'
[void][Console]::In.ReadToEnd()
$tests = @()
try {
  $tests = @(git ls-files 2>$null | Where-Object {
      $_ -match '(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*\.(test|spec)\.[a-z]+)$|(^|/)tests?/' } |
    Select-Object -First 3)
} catch { $tests = @() }
if ($tests.Count -eq 0) { exit 0 }
$runner = ''
if (($tests -join ' ') -match '\.py') {
  # Windows PowerShell turns a native command's stderr into a terminating
  # error under 'Stop'; the probe's ImportError is an answer, not a failure.
  $ErrorActionPreference = 'Continue'
  & python -c 'import pytest' 2>$null | Out-Null
  $hasPytest = $LASTEXITCODE -eq 0
  $ErrorActionPreference = 'Stop'
  $runner = if ($hasPytest) { '`python -m pytest -q`' } else { '`python -m unittest` (pytest is not installed)' }
}
if (-not $runner -and (Test-Path -LiteralPath 'package.json') -and
    ([System.IO.File]::ReadAllText((Resolve-Path 'package.json')) -match '"test"\s*:')) { $runner = '`npm test`' }
if (-not $runner) { exit 0 }
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::Out.Write("awesome-agents-md, facts about this environment: This repository's tests ($($tests -join ' ')) run with $runner from its root.`n")
