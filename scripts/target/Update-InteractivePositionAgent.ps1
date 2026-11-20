[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Plan', 'Install', 'Rollback')][string]$Action,
    [string]$ArtifactPath,
    [string]$TaskName = 'MousseControler-PositionAgent'
)

$ErrorActionPreference = 'Stop'

function Get-ManagedTask {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) { throw "Managed task not found: $TaskName" }
    $actions = @($task.Actions)
    if ($actions.Count -ne 1) { throw 'Managed task must have exactly one action' }
    $target = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($actions[0].Execute))
    if ([IO.Path]::GetFileName($target) -ne 'PositionAgent.exe') {
        throw 'Refusing to update a task that does not execute PositionAgent.exe'
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'Installed PositionAgent.exe not found' }
    [pscustomobject]@{ Task = $task; Target = $target; Arguments = $actions[0].Arguments }
}

function Get-AgentProcesses([string]$ExecutablePath) {
    $full = [IO.Path]::GetFullPath($ExecutablePath)
    @(Get-CimInstance Win32_Process -Filter "Name = 'PositionAgent.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq $full })
}

function Stop-Agent($managed) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $processes = @(Get-AgentProcesses $managed.Target)
        if ($processes.Count -eq 0) { return }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'PositionAgent did not stop within the bounded deadline'
}

$managed = Get-ManagedTask
$backup = "$($managed.Target).mc-mouse-actions.previous"
$beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash

if ($Action -eq 'Plan') {
    [ordered]@{
        task_name = $TaskName
        task_state = $managed.Task.State.ToString()
        target = $managed.Target
        arguments_present = -not [string]::IsNullOrWhiteSpace($managed.Arguments)
        installed_sha256 = $beforeHash
        backup_exists = Test-Path -LiteralPath $backup -PathType Leaf
        mutation = $false
    } | ConvertTo-Json
    exit 0
}

if ($Action -eq 'Install') {
    if (-not $ArtifactPath) { throw '-ArtifactPath is required for Install' }
    $artifact = [IO.Path]::GetFullPath($ArtifactPath)
    if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) { throw 'PositionAgent artifact not found' }
    if ([IO.Path]::GetFileName($artifact) -ne 'PositionAgent.exe') { throw 'Artifact must be named PositionAgent.exe' }
    $artifactHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash
    if ($artifactHash -eq $beforeHash) {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        [ordered]@{ changed = $false; sha256 = $beforeHash; rollback_available = (Test-Path $backup) } |
            ConvertTo-Json
        exit 0
    }
    if (Test-Path -LiteralPath $backup) {
        $backupHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash
        if ($backupHash -ne $beforeHash) { throw 'Existing rollback artifact does not match installed agent' }
    }
    Stop-Agent $managed
    if (-not (Test-Path -LiteralPath $backup)) {
        Copy-Item -LiteralPath $managed.Target -Destination $backup
    }
    $temporary = "$($managed.Target).mc-mouse-actions.new"
    Copy-Item -LiteralPath $artifact -Destination $temporary -Force
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash -ne $artifactHash) {
        Remove-Item -LiteralPath $temporary -Force
        throw 'Staged agent hash mismatch'
    }
    Move-Item -LiteralPath $temporary -Destination $managed.Target -Force
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    $task = Get-ScheduledTask -TaskName $TaskName
    if ($task.State -ne 'Running') { throw 'Updated PositionAgent task did not reach Running' }
    [ordered]@{
        changed = $true
        previous_sha256 = $beforeHash
        installed_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash
        rollback_available = $true
        task_state = $task.State.ToString()
    } | ConvertTo-Json
    exit 0
}

if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) { throw 'Rollback artifact not found' }
Stop-Agent $managed
$failed = "$($managed.Target).mc-mouse-actions.failed"
if (Test-Path -LiteralPath $failed) { throw 'Existing failed-version artifact must be handled explicitly' }
Move-Item -LiteralPath $managed.Target -Destination $failed
Copy-Item -LiteralPath $backup -Destination $managed.Target
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2
$task = Get-ScheduledTask -TaskName $TaskName
if ($task.State -ne 'Running') { throw 'Rolled-back PositionAgent task did not reach Running' }
[ordered]@{
    rolled_back = $true
    restored_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash
    failed_version = $failed
    task_state = $task.State.ToString()
} | ConvertTo-Json
