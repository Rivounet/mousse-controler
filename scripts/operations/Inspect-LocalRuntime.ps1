[CmdletBinding()]
param(
    [string]$TaskName = '\MousseControler-HOGP',
    [int]$CommandPort = 8766,
    [Parameter(DontShow)][switch]$LibraryOnly
)

$ErrorActionPreference = 'Stop'

function Test-LoopbackPort([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $attempt = $client.ConnectAsync('127.0.0.1', $Port)
        return $attempt.Wait(400) -and $client.Connected
    } catch { return $false } finally { $client.Dispose() }
}

function Get-LocalProcessInspection {
    [CmdletBinding()]
    param([scriptblock]$ProcessQuery)

    if (-not $ProcessQuery) {
        $ProcessQuery = { Get-CimInstance Win32_Process -ErrorAction Stop }
    }
    try {
        $matching = @(& $ProcessQuery | Where-Object {
            $_.CommandLine -and $_.CommandLine.IndexOf(
                'Start-MousseController.ps1', [StringComparison]::OrdinalIgnoreCase) -ge 0
        } | ForEach-Object {
            [PSCustomObject][ordered]@{
                process_id = $_.ProcessId
                session_id = $_.SessionId
                executable_leaf = [IO.Path]::GetFileName($_.ExecutablePath)
            }
        })
        [object[]]$processArray = $matching
        if ($matching.Count -eq 0) {
            $processArray = [Array]::CreateInstance([object], 0)
        }
        return [PSCustomObject]@{
            Status = 'PASS'
            ErrorType = $null
            Processes = $processArray
        }
    } catch {
        return [PSCustomObject]@{
            Status = 'BLOCKED'
            ErrorType = $_.Exception.GetType().Name
            Processes = $null
        }
    }
}

function New-LocalRuntimePayload {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$Task,
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Actions,
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Triggers,
        [AllowNull()][object]$DefinitionHash,
        [Parameter(Mandatory)][object]$ProcessInspection,
        [Parameter(Mandatory)][bool]$CommandPortOpen,
        [Parameter(Mandatory)][string]$Name
    )

    $runtime = [ordered]@{
        inspection_status = $ProcessInspection.Status
        inspection_error_type = $ProcessInspection.ErrorType
        matching_process_count = $null
        processes = $null
        command_port_open = $CommandPortOpen
    }
    if ($ProcessInspection.Status -eq 'PASS') {
        $runtime.matching_process_count = $ProcessInspection.Processes.Count
        $runtime.processes = $ProcessInspection.Processes
    }
    return [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/inspect-local-runtime-v1'
        status = if ($ProcessInspection.Status -eq 'PASS') { 'PASS' } else { 'BLOCKED' }
        task = [ordered]@{
            name = $Name
            enabled = $Task.Enabled
            state = $Task.State
            last_run_utc = if ($Task.LastRunTime -gt [datetime]::MinValue) { $Task.LastRunTime.ToUniversalTime().ToString('o') } else { $null }
            last_result = $Task.LastTaskResult
            principal = [ordered]@{
                logon_type = $Task.Definition.Principal.LogonType
                run_level = $Task.Definition.Principal.RunLevel
            }
            triggers = $Triggers
            actions = $Actions
            definition_sha256 = $DefinitionHash
        }
        runtime = $runtime
        effects = 'read-only'
    }
}

function Get-LocalRuntimeExitCode([object]$ProcessInspection) {
    if ($ProcessInspection.Status -eq 'PASS') { return 0 }
    return 2
}

if ($LibraryOnly) { return }

try {
    $scheduler = New-Object -ComObject 'Schedule.Service'
    $scheduler.Connect()
    $task = $scheduler.GetFolder('\').GetTask($TaskName.TrimStart('\'))
    $definition = $task.Definition
    $actions = @($definition.Actions | ForEach-Object {
        [ordered]@{ type = $_.Type; program = $_.Path; arguments_present = -not [string]::IsNullOrWhiteSpace($_.Arguments) }
    })
    $triggers = @($definition.Triggers | ForEach-Object {
        [ordered]@{ type = $_.Type; enabled = $_.Enabled; start_boundary_present = -not [string]::IsNullOrWhiteSpace($_.StartBoundary) }
    })
    $processInspection = Get-LocalProcessInspection
    $definitionPath = 'C:\ProgramData\MousseControler\MousseControler-HOGP.task.xml'
    $definitionHash = if (Test-Path -LiteralPath $definitionPath -PathType Leaf) {
        (Get-FileHash -LiteralPath $definitionPath -Algorithm SHA256).Hash
    } else { $null }
    $payload = New-LocalRuntimePayload -Task $task -Actions $actions -Triggers $triggers `
        -DefinitionHash $definitionHash -ProcessInspection $processInspection `
        -CommandPortOpen (Test-LoopbackPort $CommandPort) -Name $TaskName
    $payload | ConvertTo-Json -Depth 8
    $inspectionExit = Get-LocalRuntimeExitCode $processInspection
    if ($inspectionExit -ne 0) { exit $inspectionExit }
} catch [UnauthorizedAccessException] {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/inspect-local-runtime-v1'; status = 'BLOCKED'; boundary = 'windows-task-provider'; error = $_.Exception.Message } | ConvertTo-Json
    exit 2
} catch [Runtime.InteropServices.COMException] {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/inspect-local-runtime-v1'; status = 'BLOCKED'; boundary = 'windows-task-provider'; hresult = ('0x{0:X8}' -f $_.Exception.HResult) } | ConvertTo-Json
    exit 2
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/inspect-local-runtime-v1'; status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json
    exit 1
}
