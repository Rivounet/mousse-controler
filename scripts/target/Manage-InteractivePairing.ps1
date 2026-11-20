[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Start', 'Status', 'Stop')][string]$Action,
    [string]$DeviceName = 'MINI-PC-BACKEND',
    [ValidateSet('Pair', 'Inspect', 'Connect')][string]$Mode = 'Pair',
    [string]$WorkDirectory = "$env:LOCALAPPDATA\Temp\Mousse-controler-MC-HID-EXEC-001",
    [string]$TaskName = 'MousseControler-MC-HID-EXEC-001-Pairing'
)

$ErrorActionPreference = 'Stop'
$pairingTool = Join-Path $WorkDirectory 'PairingTool.exe'
$resultPath = Join-Path $WorkDirectory 'pairing-result.json'

switch ($Action) {
    'Start' {
        if (-not (Test-Path -LiteralPath $pairingTool -PathType Leaf)) { throw 'Pairing tool not found' }
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
        $modeArgument = switch ($Mode) {
            'Inspect' { '--inspect-name' }
            'Connect' { '--connect-name' }
            default { '--name' }
        }
        $arguments = '{0} "{1}" "{2}"' -f $modeArgument, $DeviceName, $resultPath
        $taskAction = New-ScheduledTaskAction -Execute $pairingTool -Argument $arguments
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Principal $principal -Settings $settings | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        [ordered]@{ task_name = $TaskName; started = $true; result_path = $resultPath } | ConvertTo-Json
    }
    'Status' {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $info = if ($task) { Get-ScheduledTaskInfo -TaskName $TaskName } else { $null }
        [ordered]@{
            task_present = ($null -ne $task)
            task_state = if ($task) { $task.State.ToString() } else { $null }
            last_task_result = if ($info) { $info.LastTaskResult } else { $null }
            result = if (Test-Path -LiteralPath $resultPath) {
                Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
            } else { $null }
        } | ConvertTo-Json -Depth 5
    }
    'Stop' {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        [ordered]@{ task_present = $false } | ConvertTo-Json
    }
}
