[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Start', 'Status', 'Stop')]
    [string]$Action,
    [string]$ExecutablePath = "$env:LOCALAPPDATA\Temp\Mousse-controler-MC-HID-EXEC-001\PositionAgent.exe",
    [string]$ConfigPath = "$env:LOCALAPPDATA\Temp\Mousse-controler-MC-HID-EXEC-001\agent.json",
    [string]$TaskName = 'MousseControler-MC-HID-EXEC-001-PositionAgent'
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class ConsoleSession {
    [DllImport("kernel32.dll")]
    public static extern uint WTSGetActiveConsoleSessionId();
}
'@

function Get-AgentTaskState {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $processes = @(Get-CimInstance Win32_Process -Filter "Name = 'PositionAgent.exe'" -ErrorAction SilentlyContinue)
    $activeConsoleSessionId = [int][ConsoleSession]::WTSGetActiveConsoleSessionId()
    [ordered]@{
        task_name = $TaskName
        task_present = ($null -ne $task)
        task_state = if ($task) { $task.State.ToString() } else { $null }
        agent_process_count = $processes.Count
        agent_session_ids = @($processes | ForEach-Object { $_.SessionId } | Sort-Object -Unique)
        active_console_session_id = $activeConsoleSessionId
        agent_is_interactive = ($null -ne $activeConsoleSessionId) -and
            (@($processes | Where-Object { $_.SessionId -eq $activeConsoleSessionId }).Count -gt 0)
    }
}

switch ($Action) {
    'Start' {
        if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) { throw 'PositionAgent executable not found' }
        if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw 'PositionAgent config not found' }
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        $taskAction = New-ScheduledTaskAction -Execute $ExecutablePath -Argument ('--config "{0}"' -f $ConfigPath)
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Principal $principal -Settings $settings | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Milliseconds 800
        Get-AgentTaskState | ConvertTo-Json -Depth 4
    }
    'Status' {
        Get-AgentTaskState | ConvertTo-Json -Depth 4
    }
    'Stop' {
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        Start-Sleep -Milliseconds 300
        Get-AgentTaskState | ConvertTo-Json -Depth 4
    }
}
