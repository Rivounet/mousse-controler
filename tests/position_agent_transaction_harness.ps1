param(
    [Parameter(Mandatory)][string]$Updater,
    [Parameter(Mandatory)][string]$Target,
    [Parameter(Mandatory)][string]$Artifact,
    [Parameter(Mandatory)][ValidateSet('Install', 'Rollback', 'Plan')][string]$Action,
    [string]$Phase = 'None'
)

$global:FakeTaskState = 'Running'

function Get-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
    [pscustomobject]@{
        State = $global:FakeTaskState
        Actions = @([pscustomobject]@{ Execute = $Target; Arguments = '--config isolated.json' })
    }
}

function Stop-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
    $global:FakeTaskState = 'Ready'
}

function Start-ScheduledTask {
    param([string]$TaskName, $ErrorAction)
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
& $Updater -Action $Action -ArtifactPath $Artifact -FaultInjectionPhase $Phase
