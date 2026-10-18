# PowerShell twin of protect.sh for agents that run Windows hooks through
# PowerShell (Codex): the same files, the same prompt.
# scripts/lint.py runs both scripts against the same edits.
$ErrorActionPreference = 'Stop'
$payload = [Console]::In.ReadToEnd()

# Claude Code names the file in file_path; Codex sends apply_patch, whose patch
# names each file on an "*** Update File:" line.
$files = @()
try {
  $toolInput = ($payload | ConvertFrom-Json).tool_input
  if ($toolInput -is [string]) { $toolInput = $toolInput | ConvertFrom-Json }
  if ($toolInput.file_path) { $files += [string]$toolInput.file_path }
} catch {}
$files += [regex]::Matches($payload, '\*\*\* (?:Update|Delete) File: ([^"\\]+)') | ForEach-Object { $_.Groups[1].Value }

$names = '^(AGENTS\.md|CLAUDE\.md|\.gitignore|\.eslintrc.*|eslint\.config\..*|\.prettierrc.*|prettier\.config\..*|biome\.jsonc?|' +
  '\.stylelintrc.*|stylelint\.config\..*|ruff\.toml|\.ruff\.toml|\.flake8|\.pylintrc|mypy\.ini|\.mypy\.ini|pytest\.ini|tox\.ini|' +
  '\.golangci\.ya?ml|\.rubocop\.yml|\.pre-commit-config\.yaml|\.?lefthook\.yml|\.gitlab-ci\.yml|' +
  '\.markdownlint.*|\.commitlintrc.*|commitlint\.config\..*)$'
foreach ($file in $files) {
  if (-not $file -or -not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
  $path = $file -replace '\\', '/'
  $name = Split-Path -Leaf $path
  if ($path -match '(^|/)(\.github/workflows|\.husky)/' -or $path -match '(^|/)\.claude/settings[^/]*\.json$' -or $name -cmatch $names) {
    [Console]::Out.WriteLine('{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"awesome-agents-md: this edits ' + $name + ', a check configuration or a file that constrains the agent. Approve only if you asked for this change."}}')
    exit 0
  }
}
exit 0
