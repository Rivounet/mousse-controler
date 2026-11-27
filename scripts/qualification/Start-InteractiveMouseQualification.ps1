[CmdletBinding()]
param(
    [ValidateSet('Start', 'Status', 'Stop')][string]$Action = 'Start',
    [string]$TaskName = 'MousseControler-MC-HID-EXEC-001-PositionAgent',
    [string]$QualificationTaskName = 'MousseControler-MouseWitness-Qualification',
    [string]$LeasePath,
    [string]$RunId,
    [string]$GitSha,
    [string]$BackendHost = 'MINI-PC-BACKEND'
)

$ErrorActionPreference = 'Stop'
$agent = Join-Path $PSScriptRoot 'PositionAgent.exe'
$updater = Join-Path $PSScriptRoot 'Update-InteractivePositionAgent.ps1'
$witness = Join-Path $PSScriptRoot 'MouseWitness.exe'
$events = Join-Path $PSScriptRoot 'witness-events.jsonl'
$state = Join-Path $PSScriptRoot 'witness-state.json'
$leaseManager = Join-Path $PSScriptRoot 'Manage-QualificationLease.ps1'

function Get-QualificationLeaseStatus {
    if (-not $LeasePath) { return $null }
    if (-not (Test-Path -LiteralPath $leaseManager -PathType Leaf)) {
        throw "Missing qualification file: $leaseManager"
    }
    & $leaseManager -Action Status -LeasePath $LeasePath | ConvertFrom-Json
}

function Assert-TargetLease {
    if (-not $LeasePath -or -not $RunId -or
            $GitSha -notmatch '^[0-9A-Fa-f]{40}([0-9A-Fa-f]{24})?$') {
        throw 'Start requires -LeasePath, -RunId and a 40- or 64-hex -GitSha'
    }
    $leaseStatus = Get-QualificationLeaseStatus
    if (-not $leaseStatus.active -or $leaseStatus.role -ne 'target' -or
            $leaseStatus.run_id -cne $RunId.ToLowerInvariant() -or
            $leaseStatus.git_sha -cne $GitSha.ToLowerInvariant() -or
            $leaseStatus.machine -cne [Environment]::MachineName.ToUpperInvariant() -or
            $leaseStatus.peer_host -cne $BackendHost.ToUpperInvariant()) {
        throw 'Active target qualification lease does not match this run and peer'
    }
    return $leaseStatus
}

function Get-WitnessProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name = 'MouseWitness.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and
            [IO.Path]::GetFullPath($_.ExecutablePath) -eq [IO.Path]::GetFullPath($witness) })
}

function Get-QualificationTask {
    $task = Get-ScheduledTask -TaskName $QualificationTaskName -ErrorAction SilentlyContinue
    if (-not $task) { return $null }
    $actions = @($task.Actions)
    if ($actions.Count -ne 1 -or
        [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($actions[0].Execute)) -ne
        [IO.Path]::GetFullPath($witness)) {
        throw "Refusing to manage unrelated task: $QualificationTaskName"
    }
    $task
}

if ($Action -eq 'Stop') {
    $task = Get-QualificationTask
    if ($task) {
        Stop-ScheduledTask -TaskName $QualificationTaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $QualificationTaskName -Confirm:$false
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    while (@(Get-WitnessProcesses).Count -gt 0 -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 100
    }
    [ordered]@{
        stopped = (@(Get-WitnessProcesses).Count -eq 0)
        task_present = ($null -ne (Get-ScheduledTask -TaskName $QualificationTaskName -ErrorAction SilentlyContinue))
    } | ConvertTo-Json
    exit 0
}

if ($Action -eq 'Status') {
    $task = Get-QualificationTask
    $processes = @(Get-WitnessProcesses)
    $leaseStatus = Get-QualificationLeaseStatus
    [ordered]@{
        task_present = ($null -ne $task)
        task_state = if ($task) { $task.State.ToString() } else { $null }
        process_ids = @($processes | ForEach-Object { $_.ProcessId })
        session_ids = @($processes | ForEach-Object { $_.SessionId } | Sort-Object -Unique)
        state_present = Test-Path -LiteralPath $state -PathType Leaf
        lease = $leaseStatus
    } | ConvertTo-Json
    exit 0
}

foreach ($required in @($agent, $updater, $witness)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing qualification file: $required" }
}

$leaseStatus = Assert-TargetLease

$update = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $updater `
    -Action Install -ArtifactPath $agent -TaskName $TaskName | ConvertFrom-Json

if (Test-Path -LiteralPath $state) { Remove-Item -LiteralPath $state -Force }
if (Test-Path -LiteralPath $events) { Remove-Item -LiteralPath $events -Force }
$existing = Get-QualificationTask
if ($existing) {
    Stop-ScheduledTask -TaskName $QualificationTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $QualificationTaskName -Confirm:$false
}
$taskAction = New-ScheduledTaskAction -Execute $witness -Argument ('"{0}" "{1}"' -f $events, $state)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $QualificationTaskName -Action $taskAction `
    -Principal $principal -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $QualificationTaskName
$deadline = [DateTime]::UtcNow.AddSeconds(10)
while (-not (Test-Path -LiteralPath $state -PathType Leaf)) {
    $processes = @(Get-WitnessProcesses)
    if ($processes.Count -eq 0 -and (Get-ScheduledTask -TaskName $QualificationTaskName).State -ne 'Running') {
        throw 'MouseWitness exited before readiness'
    }
    if ([DateTime]::UtcNow -ge $deadline) { throw 'MouseWitness readiness deadline exceeded' }
    Start-Sleep -Milliseconds 100
}
$process = @(Get-WitnessProcesses | Select-Object -First 1)
if ($process.Count -ne 1) { throw 'MouseWitness process could not be identified uniquely' }
$witnessState = Get-Content -Raw -LiteralPath $state | ConvertFrom-Json
[ordered]@{
    ready = $true
    agent_update = $update
    qualification_task = $QualificationTaskName
    witness_pid = $process[0].ProcessId
    witness_session_id = $process[0].SessionId
    witness_bounds = [ordered]@{
        x = $witnessState.x
        y = $witnessState.y
        width = $witnessState.width
        height = $witnessState.height
    }
    qualification_lease = $leaseStatus
    instruction = 'Keep the SAFE MOUSE TEST SURFACE visible until qualification completes.'
} | ConvertTo-Json -Depth 5
