[CmdletBinding()]
param(
    [string]$TaskName = 'MousseControler-PositionAgent'
)

$ErrorActionPreference = 'Stop'
$agent = Join-Path $PSScriptRoot 'PositionAgent.exe'
$updater = Join-Path $PSScriptRoot 'Update-InteractivePositionAgent.ps1'
$witness = Join-Path $PSScriptRoot 'MouseWitness.exe'
$events = Join-Path $PSScriptRoot 'witness-events.jsonl'
$state = Join-Path $PSScriptRoot 'witness-state.json'
foreach ($required in @($agent, $updater, $witness)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing qualification file: $required" }
}

$update = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $updater `
    -Action Install -ArtifactPath $agent -TaskName $TaskName | ConvertFrom-Json

if (Test-Path -LiteralPath $state) { Remove-Item -LiteralPath $state -Force }
if (Test-Path -LiteralPath $events) { Remove-Item -LiteralPath $events -Force }
$process = Start-Process -FilePath $witness -ArgumentList @($events, $state) -PassThru
$deadline = [DateTime]::UtcNow.AddSeconds(10)
while (-not (Test-Path -LiteralPath $state -PathType Leaf)) {
    if ($process.HasExited) { throw "MouseWitness exited early with code $($process.ExitCode)" }
    if ([DateTime]::UtcNow -ge $deadline) { throw 'MouseWitness readiness deadline exceeded' }
    Start-Sleep -Milliseconds 100
}
$witnessState = Get-Content -Raw -LiteralPath $state | ConvertFrom-Json
[ordered]@{
    ready = $true
    agent_update = $update
    witness_pid = $process.Id
    witness_bounds = [ordered]@{
        x = $witnessState.x
        y = $witnessState.y
        width = $witnessState.width
        height = $witnessState.height
    }
    instruction = 'Keep the SAFE MOUSE TEST SURFACE visible until qualification completes.'
} | ConvertTo-Json -Depth 5
