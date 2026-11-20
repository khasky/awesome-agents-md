# PowerShell twin of guard-switch.sh: the same command, file and messages.
# scripts/lint.py runs both scripts against the same prompts.
$ErrorActionPreference = 'Stop'

try {
  $prompt = [string]([Console]::In.ReadToEnd() | ConvertFrom-Json).prompt
} catch {
  exit 0
}
$prompt = $prompt -replace '[\r\n\t]', ' '

# Typed as text the command arrives as is; an interactive session can wrap it
# as <command-name>/awesome-agents-md:guard</command-name><command-args>push off</command-args>.
$envelope = '<command-name>\s*/awesome-agents-md:guard\s*</command-name>'
$literal = '^\s*/awesome-agents-md:guard(\s+(.*))?$'
$argText = ''
if ($prompt -cmatch $envelope) {
  if ($prompt -cmatch '<command-args>([^<]*)</command-args>') { $argText = $Matches[1] }
} elseif ($prompt -cmatch $literal) {
  $argText = [string]$Matches[2]
} else {
  exit 0
}

$userHome = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$switchFile = Join-Path $userHome '.awesome-agents-md/guard'
function Get-Switch([string]$name) {
  if ((Test-Path -LiteralPath $switchFile) -and @(Get-Content -LiteralPath $switchFile) -contains "$name=off") { 'off' } else { 'on' }
}

$words = @($argText.ToLowerInvariant() -split '\s+' | Where-Object { $_ })
$note = ''
if ($words.Count -eq 2 -and $words[0] -match '^(push|delete)$' -and $words[1] -match '^(on|off)$') {
  $null = New-Item -ItemType Directory -Force -Path (Split-Path $switchFile)
  $lines = @()
  if (Test-Path -LiteralPath $switchFile) { $lines = @(Get-Content -LiteralPath $switchFile | Where-Object { $_ -ne "$($words[0])=off" }) }
  if ($words[1] -eq 'off') { $lines += "$($words[0])=off" }
  [IO.File]::WriteAllText("$switchFile.tmp", (($lines | ForEach-Object { "$_`n" }) -join ''))
  Move-Item -Force -LiteralPath "$switchFile.tmp" -Destination $switchFile
} elseif ($words.Count -ne 0) {
  $note = 'Usage: /awesome-agents-md:guard [push|delete] [on|off]. '
}

[Console]::Out.WriteLine('{"decision":"block","reason":"awesome-agents-md guard: ' + $note + 'ask before git push: ' + (Get-Switch 'push') + '; ask before a recursive delete: ' + (Get-Switch 'delete') + '. Switch with /awesome-agents-md:guard push off, /awesome-agents-md:guard delete off, and on to restore."}')
exit 0
