param(
    [Parameter(Mandatory)][string]$Updater,
    [Parameter(Mandatory)][string]$Target,
    [Parameter(Mandatory)][string]$Artifact,
    [Parameter(Mandatory)][ValidateSet('Install', 'Rollback', 'Plan')][string]$Action,
    [string]$Phase = 'None',
    [Parameter(Mandatory)][string]$StateOutput,
    [ValidateSet('Running', 'Ready')][string]$InitialTaskState = 'Running'
)

$global:FakeTaskState = $InitialTaskState
$global:FakeStartCalls = 0
$global:FakeStopCalls = 0

function Get-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
    [pscustomobject]@{
        State = $global:FakeTaskState
        Actions = @([pscustomobject]@{ Execute = $Target; Arguments = '--config isolated.json' })
    }
}

function Stop-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
    $global:FakeStopCalls += 1
    if ($Phase -eq 'Stop') {
        throw 'Injected scheduled task stop failure'
    }
    $global:FakeTaskState = 'Ready'
}

function Start-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
    $global:FakeStartCalls += 1
    $global:FakeTaskState = 'Running'
}

function Get-CimInstance {
    param([string]$ClassName, [string]$Filter, $ErrorAction)
    if ($global:FakeTaskState -eq 'Running' -and (Test-Path -LiteralPath $Target -PathType Leaf)) {
        [pscustomobject]@{ ExecutablePath = $Target; ProcessId = 4242 }
    }
}

function Start-Sleep { param([int]$Milliseconds, [int]$Seconds) }

$env:MC_POSITION_AGENT_TRANSACTION_TEST = '1'
try {
    & $Updater -Action $Action -ArtifactPath $Artifact -FaultInjectionPhase $Phase
}
finally {
    $processCount = @(Get-CimInstance Win32_Process).Count
    $state = [ordered]@{
        task_state = $global:FakeTaskState
        process_count = $processCount
        start_calls = $global:FakeStartCalls
        stop_calls = $global:FakeStopCalls
        target_exists = Test-Path -LiteralPath $Target -PathType Leaf
        target_sha256 = if (Test-Path -LiteralPath $Target -PathType Leaf) {
            (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash
        } else { $null }
    } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText(
        $StateOutput, $state, (New-Object Text.UTF8Encoding($false))
    )
}
