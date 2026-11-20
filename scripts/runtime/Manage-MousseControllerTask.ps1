[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Start', 'Status', 'Stop')][string]$Action,
    [string]$ConfigPath,
    [string]$PythonPath = 'python.exe',
    [string]$TaskName = 'MousseControler-HOGP'
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'Start-MousseController.ps1'

if ($Action -eq 'Start') {
    if (-not $ConfigPath) { throw '-ConfigPath is required for Start' }
    $config = [IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { throw 'Controller config not found' }
    $old = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($old) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -ConfigPath "{1}" -PythonPath "{2}"' -f `
        $launcher, $config, $PythonPath
    $taskAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments `
        -WorkingDirectory ([IO.Path]::GetDirectoryName($launcher))
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $trigger `
        -Principal $principal -Settings $settings | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}
elseif ($Action -eq 'Stop') {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
[ordered]@{
    task_present = $null -ne $task
    task_state = if ($task) { $task.State.ToString() } else { $null }
    logon_trigger = if ($task) {
        @($task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' }).Count -eq 1
    } else { $false }
} | ConvertTo-Json
