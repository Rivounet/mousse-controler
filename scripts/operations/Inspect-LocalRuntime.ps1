[CmdletBinding()]
param(
    [string]$TaskName = '\MousseControler-HOGP',
    [int]$CommandPort = 8766
)

$ErrorActionPreference = 'Stop'

function Test-LoopbackPort([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $attempt = $client.ConnectAsync('127.0.0.1', $Port)
        return $attempt.Wait(400) -and $client.Connected
    } catch { return $false } finally { $client.Dispose() }
}

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
    $matchingProcesses = @()
    $processInspection = 'PASS'
    $processInspectionError = $null
    try {
        $matchingProcesses = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
            $_.CommandLine -and $_.CommandLine.IndexOf('Start-MousseController.ps1', [StringComparison]::OrdinalIgnoreCase) -ge 0
        } | ForEach-Object {
            [ordered]@{ process_id = $_.ProcessId; session_id = $_.SessionId; executable_leaf = [IO.Path]::GetFileName($_.ExecutablePath) }
        })
    } catch {
        $matchingProcesses = @()
        $processInspection = 'BLOCKED'
        $processInspectionError = $_.Exception.GetType().Name
    }
    $definitionPath = 'C:\ProgramData\MousseControler\MousseControler-HOGP.task.xml'
    $definitionHash = if (Test-Path -LiteralPath $definitionPath -PathType Leaf) {
        (Get-FileHash -LiteralPath $definitionPath -Algorithm SHA256).Hash
    } else { $null }
    [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/inspect-local-runtime-v1'
        status = if ($processInspection -eq 'PASS') { 'PASS' } else { 'BLOCKED' }
        task = [ordered]@{
            name = $TaskName
            enabled = $task.Enabled
            state = $task.State
            last_run_utc = if ($task.LastRunTime -gt [datetime]::MinValue) { $task.LastRunTime.ToUniversalTime().ToString('o') } else { $null }
            last_result = $task.LastTaskResult
            principal = [ordered]@{ logon_type = $definition.Principal.LogonType; run_level = $definition.Principal.RunLevel }
            triggers = $triggers
            actions = $actions
            definition_sha256 = $definitionHash
        }
        runtime = [ordered]@{
            inspection_status = $processInspection
            inspection_error_type = $processInspectionError
            matching_process_count = if ($processInspection -eq 'PASS') { $matchingProcesses.Count } else { $null }
            processes = if ($processInspection -eq 'PASS') { $matchingProcesses } else { $null }
            command_port_open = Test-LoopbackPort $CommandPort
        }
        effects = 'read-only'
    } | ConvertTo-Json -Depth 8
    if ($processInspection -ne 'PASS') { exit 2 }
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
