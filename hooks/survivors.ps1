# Processes the agent started this turn and left running, at three moments of
# the turn: start (UserPromptSubmit) records every process under the agent;
# after (PostToolUse on a shell call) names those started since that still run;
# stop (Stop) sends the turn back once while any do, so a server, watch or
# browser is stopped or explained instead of left holding memory and ports.
# MCP and language servers predate the turn and never count. Known ceiling: a
# process whose parent already exited is no longer under the agent (Windows
# keeps a dead parent id, Unix reparents it) and is not seen.
# Git Bash cannot see Windows process parents, so survivors.sh runs this script
# on Windows, and this script runs survivors.sh everywhere else.
param([string]$Mode)
$ErrorActionPreference = 'Stop'
$text = [Console]::In.ReadToEnd()
if ($env:OS -ne 'Windows_NT') {
  $text | bash "$PSScriptRoot/survivors.sh" $Mode
  exit $LASTEXITCODE
}
# The second stop in a turn is always allowed, so the agent can say why a
# process keeps running instead of being held in a loop.
if ($Mode -eq 'stop') {
  try { if (($text | ConvertFrom-Json).stop_hook_active -eq $true) { exit 0 } } catch { }
}

$procs = @{}
foreach ($p in Get-CimInstance Win32_Process) { $procs[[int]$p.ProcessId] = $p }
# Git Bash's parent links from survivors.sh, for the Git Bash programs whose
# Windows parent has exited.
$msys = @{}
foreach ($pair in ([string]$env:AWESOME_AGENTS_MD_MSYS_PARENTS).Split(' ', [StringSplitOptions]::RemoveEmptyEntries)) {
  $win, $up = $pair.Split(':')
  $msys[[int]$win] = [int]$up
}
function Test-Parent($up, $p) {
  # A dead parent's id can be reused by a younger process, which is no parent.
  $up -and $up.ProcessId -ne $p.ProcessId -and $up.CreationDate -le $p.CreationDate
}
function Get-Parent($p) {
  $up = $procs[[int]$p.ParentProcessId]
  if (Test-Parent $up $p) { return $up }
  if ($msys.ContainsKey([int]$p.ProcessId)) {
    $up = $procs[$msys[[int]$p.ProcessId]]
    if (Test-Parent $up $p) { return $up }
  }
}
function Get-Key($p) { "$($p.ProcessId)@$($p.CreationDate.Ticks)" }

# The agent is the nearest ancestor that is not a shell; root is the process
# under it this hook runs in, which a hook running beside this one shares the
# start time of.
$shells = '^(bash|sh|dash|zsh|ksh|fish|cmd|pwsh|powershell)(\.exe)?$'
$root = $procs[$PID]
$agent = Get-Parent $root
while ($agent -and $agent.Name -match $shells) { $root = $agent; $agent = Get-Parent $agent }
if (-not $agent -or $agent.ProcessId -le 4) { exit 0 }
$state = Join-Path ([IO.Path]::GetTempPath()) ("awesome-agents-md-survivors-$(Get-Key $agent).txt" -replace '@', '-')

$children = @{}
foreach ($p in $procs.Values) {
  $up = Get-Parent $p
  if ($up) { $children[[int]$up.ProcessId] = @($children[[int]$up.ProcessId]) + $p }
}
# Every process under the agent, each with the agent's child it descends from.
$found = [Collections.Generic.List[object]]::new()
$queue = [Collections.Generic.Queue[object]]::new()
foreach ($c in @($children[[int]$agent.ProcessId])) { if ($c) { $queue.Enqueue(@($c, $c, $agent)) } }
while ($queue.Count) {
  $c, $top, $up = $queue.Dequeue()
  $found.Add([pscustomobject]@{ P = $c; Top = $top; Up = [int]$up.ProcessId })
  foreach ($k in @($children[[int]$c.ProcessId])) { if ($k) { $queue.Enqueue(@($k, $top, $c)) } }
}

if ($Mode -eq 'start') {
  [IO.File]::WriteAllLines($state, [string[]](@('awesome-agents-md survivors') + @($found | ForEach-Object { Get-Key $_.P })))
  exit 0
}
if (-not (Test-Path -LiteralPath $state)) { exit 0 }
$lines = [IO.File]::ReadAllLines($state)
if ($lines[0] -ne 'awesome-agents-md survivors') { exit 0 }
$known = [Collections.Generic.HashSet[string]]::new([string[]]$lines)
# A tree that began within a second of this hook is a hook running beside it.
$fence = $root.CreationDate.AddSeconds(-1)
$fresh = @($found | Where-Object {
    -not $known.Contains((Get-Key $_.P)) -and $_.Top.CreationDate -lt $fence -and $_.P.Name -ne 'conhost.exe' })
$ids = [Collections.Generic.HashSet[int]]::new([int[]]@($fresh | ForEach-Object { [int]$_.P.ProcessId }))
$named = @($fresh | Where-Object { -not $ids.Contains($_.Up) } | ForEach-Object {
    $command = ([string]$_.P.CommandLine -replace '\s+', ' ').Trim()
    if ($command.Length -gt 100) { $command = $command.Substring(0, 100) + '...' }
    "$($_.P.ProcessId) $($_.P.Name) ($command)" })
if ($named.Count -eq 0) { exit 0 }
$list = ($named | Select-Object -First 10) -join '; '
if ($named.Count -gt 10) { $list += "; and $($named.Count - 10) more" }

if ($Mode -eq 'stop') {
  [Console]::Error.WriteLine("Processes you started this turn are still running ($($named.Count)): $list. Stop each one whose job is done, by these process ids and their children only, or say why it keeps running.")
  exit 2
}
$out = @{ hookSpecificOutput = @{ hookEventName = 'PostToolUse'
    additionalContext = "awesome-agents-md: still running from this turn ($($named.Count)): $list. Stop the ones whose job is done before you finish." } } |
  ConvertTo-Json -Compress
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::Out.Write($out + "`n")
