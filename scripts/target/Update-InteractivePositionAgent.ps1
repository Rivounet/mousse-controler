[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Plan', 'Install', 'Rollback')][string]$Action,
    [string]$ArtifactPath,
    [string]$TaskName = 'MousseControler-PositionAgent',
    [Parameter(DontShow)][ValidateSet(
        'None', 'Preparation', 'Stop', 'Backup', 'Staging', 'Replacement',
        'Installation', 'Start', 'Verification', 'Confirmation', 'Restore',
        'RestartAfterRestore', 'RecoveryRestart', 'RecoveryVerification',
        'RollbackBeforeMutation', 'RollbackAfterPreserve', 'RollbackCopy',
        'RollbackPartialCopy', 'RollbackBeforeValidation', 'RollbackValidation',
        'RollbackAfterMutation', 'RollbackStart', 'RollbackVerification',
        'RollbackCompensation'
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
    $target = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($actions[0].Execute)
    )
    if ([IO.Path]::GetFileName($target) -ne 'PositionAgent.exe') {
        throw 'Refusing to update a task that does not execute PositionAgent.exe'
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw 'Installed PositionAgent.exe not found'
    }
    [pscustomobject]@{
        Task = $task
        Target = $target
        Arguments = $actions[0].Arguments
    }
}

function Get-AgentProcesses([string]$ExecutablePath) {
    $full = [IO.Path]::GetFullPath($ExecutablePath)
    @(Get-CimInstance Win32_Process -Filter "Name = 'PositionAgent.exe'" `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            [IO.Path]::GetFullPath($_.ExecutablePath) -eq $full
        })
}

function Get-RuntimeSnapshot($managed) {
    $task = Get-ScheduledTask -TaskName $TaskName
    $processes = @(Get-AgentProcesses $managed.Target)
    [pscustomobject]@{
        TaskState = $task.State.ToString()
        ProcessCount = $processes.Count
        WasActive = ($task.State -eq 'Running' -or $processes.Count -gt 0)
        WasHealthy = ($task.State -eq 'Running' -and $processes.Count -gt 0)
    }
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
        if ($task.State -eq 'Running' -and $processes.Count -gt 0) {
            return $task
        }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Write-TransactionState([string]$Path, [hashtable]$State) {
    $temporary = "$Path.tmp"
    $json = [ordered]@{
        version = 1
        operation = $State.operation
        phase = $State.phase
        previous_sha256 = $State.previous_sha256
        candidate_sha256 = $State.candidate_sha256
        initial_task_state = $State.initial_task_state
        initial_process_count = $State.initial_process_count
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

function Write-RecoveryRequired(
        [string]$StatePath, [string]$Operation, [string]$PreviousHash,
        [string]$CandidateHash, $Initial, [int]$Attempts, [string]$Message) {
    Write-TransactionState $StatePath @{
        operation = $Operation
        phase = 'RECOVERY_REQUIRED'
        previous_sha256 = $PreviousHash
        candidate_sha256 = $CandidateHash
        initial_task_state = $Initial.TaskState
        initial_process_count = $Initial.ProcessCount
        restore_attempts = $Attempts
        error = $Message
    }
}

function Restore-InitialRuntime(
        $managed, $Initial, [string]$ExpectedHash, [string]$StatePath,
        [string]$Operation, [string]$CandidateHash,
        [string]$RestartFault, [string]$VerificationFault) {
    if (-not $Initial.WasActive) {
        Remove-TransactionState $StatePath
        return $true
    }
    $current = Get-RuntimeSnapshot $managed
    if ($current.WasHealthy -and
            (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -eq
                $ExpectedHash) {
        Remove-TransactionState $StatePath
        return $true
    }
    $errors = @()
    for ($attempt = 1; $attempt -le $script:MaximumRestoreAttempts; $attempt++) {
        try {
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -ne
                    $ExpectedHash) {
                throw 'Preserved PositionAgent hash mismatch during runtime recovery'
            }
            Invoke-FaultInjection $RestartFault
            Start-ScheduledTask -TaskName $TaskName
            Invoke-FaultInjection $VerificationFault
            $null = Wait-AgentHealthy $managed `
                'Preserved PositionAgent task did not recover to Running'
            Remove-TransactionState $StatePath
            return $true
        }
        catch {
            $errors += $_.Exception.Message
        }
    }
    Write-RecoveryRequired $StatePath $Operation $ExpectedHash $CandidateHash `
        $Initial $script:MaximumRestoreAttempts ($errors -join ' | ')
    return $false
}

function Restore-PreviousVersion(
        $managed, [string]$Backup, [string]$PreviousHash,
        [string]$CandidateHash, [string]$StatePath, $Initial) {
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
                operation = 'Install'
                phase = 'RESTORED'
                previous_sha256 = $PreviousHash
                candidate_sha256 = $CandidateHash
                initial_task_state = $Initial.TaskState
                initial_process_count = $Initial.ProcessCount
                restore_attempts = $attempt
                error = $null
            }
            Invoke-FaultInjection 'RestartAfterRestore'
            Start-ScheduledTask -TaskName $TaskName
            $null = Wait-AgentHealthy $managed `
                'Restored PositionAgent task did not reach Running'
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
    Write-RecoveryRequired $StatePath 'Install' $PreviousHash $CandidateHash `
        $Initial $script:MaximumRestoreAttempts ($errors -join ' | ')
    return $false
}

function Restore-PreservedCurrent(
        $managed, [string]$Preserved, [string]$CurrentHash,
        [string]$BackupHash, [string]$StatePath, $Initial) {
    $errors = @()
    for ($attempt = 1; $attempt -le $script:MaximumRestoreAttempts; $attempt++) {
        $compensationTemporary = "$($managed.Target).mc-mouse-actions.compensate"
        try {
            Stop-Agent $managed
            Invoke-FaultInjection 'RollbackCompensation'
            Copy-Item -LiteralPath $Preserved -Destination $compensationTemporary -Force
            if ((Get-FileHash -Algorithm SHA256 `
                    -LiteralPath $compensationTemporary).Hash -ne $CurrentHash) {
                throw 'Rollback compensation staging hash mismatch'
            }
            Move-Item -LiteralPath $compensationTemporary `
                -Destination $managed.Target -Force
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -ne
                    $CurrentHash) {
                throw 'Rollback compensation installed hash mismatch'
            }
            if ($Initial.WasActive) {
                Start-ScheduledTask -TaskName $TaskName
                $null = Wait-AgentHealthy $managed `
                    'Compensated PositionAgent task did not reach Running'
            }
            Remove-TransactionState $StatePath
            return $true
        }
        catch {
            $errors += $_.Exception.Message
            if (Test-Path -LiteralPath $compensationTemporary) {
                Remove-Item -LiteralPath $compensationTemporary -Force
            }
        }
    }
    Write-RecoveryRequired $StatePath 'Rollback' $CurrentHash $BackupHash `
        $Initial $script:MaximumRestoreAttempts ($errors -join ' | ')
    return $false
}

$managed = Get-ManagedTask
$backup = "$($managed.Target).mc-mouse-actions.previous"
$statePath = "$($managed.Target).mc-update-state.json"
$beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash

if ($Action -eq 'Plan') {
    $transactionState = $null
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        try {
            $transactionState = (
                Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
            ).phase
        }
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
    return
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
            changed = $false
            sha256 = $beforeHash
            rollback_available = (Test-Path -LiteralPath $backup -PathType Leaf)
        } | ConvertTo-Json
        return
    }

    $initial = Get-RuntimeSnapshot $managed
    $replacementStarted = $false
    $temporary = "$($managed.Target).mc-mouse-actions.new"
    try {
        Stop-Agent $managed
        Invoke-FaultInjection 'Stop'
        Write-TransactionState $statePath @{
            operation = 'Install'
            phase = 'PREPARED'
            previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash
            initial_task_state = $initial.TaskState
            initial_process_count = $initial.ProcessCount
            restore_attempts = 0
            error = $null
        }
        if ($FaultInjectionPhase -eq 'RecoveryRestart' -or
                $FaultInjectionPhase -eq 'RecoveryVerification') {
            throw 'Injected pre-replacement failure for runtime recovery test'
        }
        Invoke-FaultInjection 'Backup'
        if (Test-Path -LiteralPath $backup -PathType Leaf) {
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne
                    $beforeHash) {
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
            operation = 'Install'
            phase = 'BACKED_UP'
            previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash
            initial_task_state = $initial.TaskState
            initial_process_count = $initial.ProcessCount
            restore_attempts = 0
            error = $null
        }

        Invoke-FaultInjection 'Staging'
        Copy-Item -LiteralPath $artifact -Destination $temporary -Force
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash -ne
                $artifactHash) {
            throw 'Staged agent hash mismatch'
        }
        Invoke-FaultInjection 'Replacement'
        $replacementStarted = $true
        Move-Item -LiteralPath $temporary -Destination $managed.Target -Force
        Write-TransactionState $statePath @{
            operation = 'Install'
            phase = 'REPLACED'
            previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash
            initial_task_state = $initial.TaskState
            initial_process_count = $initial.ProcessCount
            restore_attempts = 0
            error = $null
        }
        if ($FaultInjectionPhase -eq 'Restore' -or
                $FaultInjectionPhase -eq 'RestartAfterRestore') {
            throw 'Injected PositionAgent transaction failure: Installation'
        }
        Invoke-FaultInjection 'Installation'
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -ne
                $artifactHash) {
            throw 'Installed PositionAgent hash mismatch'
        }
        Invoke-FaultInjection 'Start'
        Start-ScheduledTask -TaskName $TaskName
        Invoke-FaultInjection 'Verification'
        $task = Wait-AgentHealthy $managed `
            'Updated PositionAgent task did not reach Running'
        Write-TransactionState $statePath @{
            operation = 'Install'
            phase = 'VALIDATED'
            previous_sha256 = $beforeHash
            candidate_sha256 = $artifactHash
            initial_task_state = $initial.TaskState
            initial_process_count = $initial.ProcessCount
            restore_attempts = 0
            error = $null
        }
        Invoke-FaultInjection 'Confirmation'
        Remove-TransactionState $statePath
        [ordered]@{
            changed = $true
            previous_sha256 = $beforeHash
            installed_sha256 = (
                Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target
            ).Hash
            rollback_available = $true
            task_state = $task.State.ToString()
        } | ConvertTo-Json
        return
    }
    catch {
        $installFailure = $_.Exception
        if (-not $replacementStarted) {
            if (Test-Path -LiteralPath $temporary) {
                Remove-Item -LiteralPath $temporary -Force
            }
            $recovered = Restore-InitialRuntime $managed $initial $beforeHash `
                $statePath 'Install' $artifactHash 'RecoveryRestart' `
                'RecoveryVerification'
            if ($recovered) {
                throw (New-Object InvalidOperationException(
                    "PositionAgent update failed before replacement; previous runtime state was restored: $($installFailure.Message)",
                    $installFailure
                ))
            }
            throw (New-Object InvalidOperationException(
                "PositionAgent update failed before replacement; recovery required: $($installFailure.Message)",
                $installFailure
            ))
        }
        $restored = Restore-PreviousVersion $managed $backup $beforeHash `
            $artifactHash $statePath $initial
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
$backupHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash
$initial = Get-RuntimeSnapshot $managed
$failed = "$($managed.Target).mc-mouse-actions.failed"
$failedTemporary = "$failed.tmp"
$rollbackTemporary = "$($managed.Target).mc-mouse-actions.rollback"
if (Test-Path -LiteralPath $failed) {
    throw 'Existing failed-version artifact must be handled explicitly'
}
$rollbackMutationStarted = $false
Write-TransactionState $statePath @{
    operation = 'Rollback'
    phase = 'ROLLBACK_PREPARED'
    previous_sha256 = $beforeHash
    candidate_sha256 = $backupHash
    initial_task_state = $initial.TaskState
    initial_process_count = $initial.ProcessCount
    restore_attempts = 0
    error = $null
}
try {
    Stop-Agent $managed
    Invoke-FaultInjection 'RollbackBeforeMutation'

    Copy-Item -LiteralPath $managed.Target -Destination $failedTemporary -Force
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $failedTemporary).Hash -ne
            $beforeHash) {
        throw 'Preserved current PositionAgent hash mismatch'
    }
    Move-Item -LiteralPath $failedTemporary -Destination $failed -Force
    Invoke-FaultInjection 'RollbackAfterPreserve'

    Invoke-FaultInjection 'RollbackCopy'
    if ($FaultInjectionPhase -eq 'RollbackPartialCopy') {
        $bytes = [IO.File]::ReadAllBytes($backup)
        $partialLength = [Math]::Max(1, [Math]::Floor($bytes.Length / 2))
        [IO.File]::WriteAllBytes(
            $rollbackTemporary,
            $bytes[0..($partialLength - 1)]
        )
        throw 'Injected PositionAgent transaction failure: RollbackPartialCopy'
    }
    Copy-Item -LiteralPath $backup -Destination $rollbackTemporary -Force
    Invoke-FaultInjection 'RollbackBeforeValidation'
    Invoke-FaultInjection 'RollbackValidation'
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $rollbackTemporary).Hash -ne
            $backupHash) {
        throw 'Rollback staging hash mismatch'
    }
    Write-TransactionState $statePath @{
        operation = 'Rollback'
        phase = 'ROLLBACK_REPLACING'
        previous_sha256 = $beforeHash
        candidate_sha256 = $backupHash
        initial_task_state = $initial.TaskState
        initial_process_count = $initial.ProcessCount
        restore_attempts = 0
        error = $null
    }
    $rollbackMutationStarted = $true
    Move-Item -LiteralPath $rollbackTemporary -Destination $managed.Target -Force
    Invoke-FaultInjection 'RollbackAfterMutation'
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $managed.Target).Hash -ne
            $backupHash) {
        throw 'Rolled-back PositionAgent hash mismatch'
    }
    if ($FaultInjectionPhase -eq 'RollbackCompensation') {
        throw 'Injected rollback failure before compensation test'
    }
    Invoke-FaultInjection 'RollbackStart'
    Start-ScheduledTask -TaskName $TaskName
    Invoke-FaultInjection 'RollbackVerification'
    $task = Wait-AgentHealthy $managed `
        'Rolled-back PositionAgent task did not reach Running'
    Remove-TransactionState $statePath
    [ordered]@{
        rolled_back = $true
        restored_sha256 = $backupHash
        failed_version = $failed
        task_state = $task.State.ToString()
    } | ConvertTo-Json
}
catch {
    $rollbackFailure = $_.Exception
    if (Test-Path -LiteralPath $failedTemporary) {
        Remove-Item -LiteralPath $failedTemporary -Force
    }
    if (Test-Path -LiteralPath $rollbackTemporary) {
        Remove-Item -LiteralPath $rollbackTemporary -Force
    }

    if (-not $rollbackMutationStarted) {
        $recovered = Restore-InitialRuntime $managed $initial $beforeHash `
            $statePath 'Rollback' $backupHash 'RollbackStart' `
            'RollbackVerification'
        if ($recovered) {
            if (Test-Path -LiteralPath $failed) {
                Remove-Item -LiteralPath $failed -Force
            }
            throw (New-Object InvalidOperationException(
                "PositionAgent rollback failed before replacement; original runtime state was restored: $($rollbackFailure.Message)",
                $rollbackFailure
            ))
        }
        throw (New-Object InvalidOperationException(
            "PositionAgent rollback failed before replacement; recovery required: $($rollbackFailure.Message)",
            $rollbackFailure
        ))
    }

    $compensated = Restore-PreservedCurrent $managed $failed $beforeHash `
        $backupHash $statePath $initial
    if ($compensated) {
        if (Test-Path -LiteralPath $failed) {
            Remove-Item -LiteralPath $failed -Force
        }
        throw (New-Object InvalidOperationException(
            "PositionAgent rollback failed and original version was restored: $($rollbackFailure.Message)",
            $rollbackFailure
        ))
    }
    throw (New-Object InvalidOperationException(
        "PositionAgent rollback failed; recovery required: $($rollbackFailure.Message)",
        $rollbackFailure
    ))
}
