[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Plan', 'Install', 'Rollback')][string]$Action,
    [string]$ArtifactPath,
    [string]$TaskName = 'MousseControler-PositionAgent',
    [Parameter(DontShow)][ValidateSet(
        'None', 'Preparation', 'Backup', 'Replacement', 'Installation',
        'Start', 'Verification', 'Confirmation', 'Restore',
        'RestartAfterRestore'
    )][string]$FaultInjectionPhase = 'None'
)

$ErrorActionPreference = 'Stop'
$script:MaximumRestoreAttempts = 2

if ($FaultInjectionPhase -ne 'None' -and
        $env:MC_POSITION_AGENT_TRANSACTION_TEST -ne '1') {
    throw 'Fault injection is restricted to the isolated transaction test harness'
}

function Invoke-FaultInjection([string]$Phase) {
    if ($FaultInjectionPhase -eq $Phase) {
        throw "Injected PositionAgent transaction failure: $Phase"
    }
}

function Get-ManagedTask {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) { throw "Managed task not found: $TaskName" }
    $actions = @($task.Actions)
    if ($actions.Count -ne 1) { throw 'Managed task must have exactly one action' }
    $target = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($actions[0].Execute))
    if ([IO.Path]::GetFileName($target) -ne 'PositionAgent.exe') {
        throw 'Refusing to update a task that does not execute PositionAgent.exe'
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw 'Installed PositionAgent.exe not found'
    }
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

function Wait-AgentHealthy($managed, [string]$FailureMessage) {
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $task = Get-ScheduledTask -TaskName $TaskName
        $processes = @(Get-AgentProcesses $managed.Target)
        if ($task.State -eq 'Running' -and $processes.Count -gt 0) { return $task }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Write-TransactionState([string]$Path, [hashtable]$State) {
    $temporary = "$Path.tmp"
    $json = [ordered]@{
        version = 1
        phase = $State.phase
        previous_sha256 = $State.previous_sha256
        candidate_sha256 = $State.candidate_sha256
        restore_attempts = $State.restore_attempts
        error = $State.error
    } | ConvertTo-Json -Compress
    $encoding = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($temporary, $json, $encoding)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Remove-TransactionState([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force
    }
}

function Restore-PreviousVersion($managed, [string]$Backup, [string]$PreviousHash,
                                [string]$CandidateHash, [string]$StatePath) {
    $errors = @()
    for ($attempt = 1; $attempt -le $script:MaximumRestoreAttempts; $attempt++) {
        $restoreTemporary = "$($managed.Target).mc-mouse-actions.restore"
        try {
            Stop-Agent $managed
            Invoke-FaultInjection 'Restore'
            Copy-Item -LiteralPath $Backup -Destination $restoreTemporary -Force
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $restoreTemporary).Hash -ne
                    $PreviousHash) {
                throw 'Restored PositionAgent hash mismatch'
            }
            Move-Item -LiteralPath $restoreTemporary -Destination $managed.Target -Force
            Write-TransactionState $StatePath @{
                phase = 'RESTORED'; previous_sha256 = $PreviousHash
                candidate_sha256 = $CandidateHash; restore_attempts = $attempt; error = $null
            }
            Invoke-FaultInjection 'RestartAfterRestore'
            Start-ScheduledTask -TaskName $TaskName
            $null = Wait-AgentHealthy $managed 'Restored PositionAgent task did not reach Running'
            Remove-TransactionState $StatePath
            return $true
        }
        catch {
            $errors += $_.Exception.Message
            if (Test-Path -LiteralPath $restoreTemporary) {
                Remove-Item -LiteralPath $restoreTemporary -Force
            }
        }
    }
    Write-TransactionState $StatePath @{
        phase = 'RECOVERY_REQUIRED'; previous_sha256 = $PreviousHash
        candidate_sha256 = $CandidateHash; restore_attempts = $script:MaximumRestoreAttempts
        error = ($errors -join ' | ')
    }
    return $false
}

$managed = Get-ManagedTask
$backup = "$($managed.Target).mc-mouse-actions.previous"
$statePath = "$($managed.Target).mc-update-state.json"
$beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash

if ($Action -eq 'Plan') {
    $transactionState = $null
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        try { $transactionState = (Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json).phase }
        catch { $transactionState = 'INVALID_STATE' }
    }
    [ordered]@{
        task_name = $TaskName
        task_state = $managed.Task.State.ToString()
        target = $managed.Target
        arguments_present = -not [string]::IsNullOrWhiteSpace($managed.Arguments)
        installed_sha256 = $beforeHash
        backup_exists = Test-Path -LiteralPath $backup -PathType Leaf
        transaction_state = $transactionState
        mutation = $false
    } | ConvertTo-Json
    exit 0
}

if ($Action -eq 'Install') {
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        throw 'Incomplete PositionAgent transaction requires explicit recovery before Install'
    }
    Invoke-FaultInjection 'Preparation'
    if (-not $ArtifactPath) { throw '-ArtifactPath is required for Install' }
    $artifact = [IO.Path]::GetFullPath($ArtifactPath)
    if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
        throw 'PositionAgent artifact not found'
    }
    if ([IO.Path]::GetFileName($artifact) -ne 'PositionAgent.exe') {
        throw 'Artifact must be named PositionAgent.exe'
    }
    $artifactHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash
    if ($artifactHash -eq $beforeHash) {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        [ordered]@{
            changed = $false; sha256 = $beforeHash
            rollback_available = (Test-Path -LiteralPath $backup -PathType Leaf)
        } | ConvertTo-Json
        exit 0
    }

    $replacementStarted = $false
    $temporary = "$($managed.Target).mc-mouse-actions.new"
    try {
        Stop-Agent $managed
        Write-TransactionState $statePath @{
            phase = 'PREPARED'; previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash; restore_attempts = 0; error = $null
        }
        Invoke-FaultInjection 'Backup'
        if (Test-Path -LiteralPath $backup -PathType Leaf) {
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne $beforeHash) {
                throw 'Existing rollback artifact does not match installed agent'
            }
        }
        else {
            Copy-Item -LiteralPath $managed.Target -Destination $backup
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne $beforeHash) {
            throw 'Rollback artifact hash mismatch'
        }
        Write-TransactionState $statePath @{
            phase = 'BACKED_UP'; previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash; restore_attempts = 0; error = $null
        }

        Copy-Item -LiteralPath $artifact -Destination $temporary -Force
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash -ne $artifactHash) {
            throw 'Staged agent hash mismatch'
        }
        Invoke-FaultInjection 'Replacement'
        Move-Item -LiteralPath $temporary -Destination $managed.Target -Force
        $replacementStarted = $true
        Write-TransactionState $statePath @{
            phase = 'REPLACED'; previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash; restore_attempts = 0; error = $null
        }
        if ($FaultInjectionPhase -eq 'Restore' -or
                $FaultInjectionPhase -eq 'RestartAfterRestore') {
            throw 'Injected PositionAgent transaction failure: Installation'
        }
        Invoke-FaultInjection 'Installation'
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -ne $artifactHash) {
            throw 'Installed PositionAgent hash mismatch'
        }
        Invoke-FaultInjection 'Start'
        Start-ScheduledTask -TaskName $TaskName
        Invoke-FaultInjection 'Verification'
        $task = Wait-AgentHealthy $managed 'Updated PositionAgent task did not reach Running'
        Write-TransactionState $statePath @{
            phase = 'VALIDATED'; previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash; restore_attempts = 0; error = $null
        }
        Invoke-FaultInjection 'Confirmation'
        Remove-TransactionState $statePath
        [ordered]@{
            changed = $true
            previous_sha256 = $beforeHash
            installed_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash
            rollback_available = $true
            task_state = $task.State.ToString()
        } | ConvertTo-Json
        exit 0
    }
    catch {
        $installFailure = $_.Exception
        if (-not $replacementStarted) {
            if (Test-Path -LiteralPath $temporary) {
                Remove-Item -LiteralPath $temporary -Force
            }
            Remove-TransactionState $statePath
            throw
        }
        $restored = Restore-PreviousVersion $managed $backup $beforeHash $artifactHash $statePath
        if ($restored) {
            throw (New-Object InvalidOperationException(
                "PositionAgent update failed and previous version was restored: $($installFailure.Message)",
                $installFailure
            ))
        }
        throw (New-Object InvalidOperationException(
            "PositionAgent update failed; recovery required: $($installFailure.Message)",
            $installFailure
        ))
    }
}

if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
    throw 'Rollback artifact not found'
}
Stop-Agent $managed
$failed = "$($managed.Target).mc-mouse-actions.failed"
if (Test-Path -LiteralPath $failed) {
    throw 'Existing failed-version artifact must be handled explicitly'
}
try {
    Move-Item -LiteralPath $managed.Target -Destination $failed
    Copy-Item -LiteralPath $backup -Destination $managed.Target
    $restoredHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash
    $backupHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash
    if ($restoredHash -ne $backupHash) { throw 'Rolled-back PositionAgent hash mismatch' }
    Start-ScheduledTask -TaskName $TaskName
    $task = Wait-AgentHealthy $managed 'Rolled-back PositionAgent task did not reach Running'
    Remove-TransactionState $statePath
    [ordered]@{
        rolled_back = $true
        restored_sha256 = $restoredHash
        failed_version = $failed
        task_state = $task.State.ToString()
    } | ConvertTo-Json
}
catch {
    $rollbackFailure = $_.Exception
    if (-not (Test-Path -LiteralPath $managed.Target -PathType Leaf) -and
            (Test-Path -LiteralPath $failed -PathType Leaf)) {
        Copy-Item -LiteralPath $failed -Destination $managed.Target
    }
    Write-TransactionState $statePath @{
        phase = 'RECOVERY_REQUIRED'; previous_sha256 = $beforeHash
        candidate_sha256 = $null; restore_attempts = 1; error = $rollbackFailure.Message
    }
    throw (New-Object InvalidOperationException(
        "PositionAgent rollback failed; recovery required: $($rollbackFailure.Message)",
        $rollbackFailure
    ))
}
