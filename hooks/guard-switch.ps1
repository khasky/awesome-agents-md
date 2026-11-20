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

function Get-Label([string]$name) {
  if ($name -eq 'push') { 'push' } else { 'recursive-delete' }
}
# One line per switch: its state and the command that flips it.
function Get-Line([string]$name) {
  $now = Get-Switch $name
  $flip = if ($now -eq 'on') { 'off' } else { 'on' }
  "$(Get-Label $name) prompt: $now (/awesome-agents-md:guard $name $flip)"
}

$words = @($argText.ToLowerInvariant() -split '\s+' | Where-Object { $_ })
$title = 'awesome-agents-md guard:'
if ($words.Count -eq 2 -and $words[0] -match '^(push|delete)$' -and $words[1] -match '^(on|off)$') {
  if ((Get-Switch $words[0]) -eq $words[1]) {
    $title += " $(Get-Label $words[0]) prompt is already $($words[1])."
  } else {
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $switchFile)
    $lines = @()
    if (Test-Path -LiteralPath $switchFile) { $lines = @(Get-Content -LiteralPath $switchFile | Where-Object { $_ -ne "$($words[0])=off" }) }
    if ($words[1] -eq 'off') { $lines += "$($words[0])=off" }
    [IO.File]::WriteAllText("$switchFile.tmp", (($lines | ForEach-Object { "$_`n" }) -join ''))
    Move-Item -Force -LiteralPath "$switchFile.tmp" -Destination $switchFile
    $title += " $(Get-Label $words[0]) prompt turned $($words[1])."
  }
} elseif ($words.Count -ne 0) {
  $title += ' usage: /awesome-agents-md:guard [push|delete] [on|off].'
}

[Console]::Out.WriteLine('{"decision":"block","reason":"' + $title + '\n' + (Get-Line 'push') + '\n' + (Get-Line 'delete') + '"}')
exit 0
