[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Start', 'Status', 'Stop')][string]$Action,
    [string]$ConfigPath,
    [string]$PythonPath = 'python.exe',
    [string]$TaskName = 'MousseControler-HOGP'
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'Start-MousseController.ps1'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Stop-ManagedRuntime($Task) {
    $taskAction = @($Task.Actions)[0]
    $expectedLauncher = '-File "{0}"' -f $launcher
    if ($taskAction.Execute -ne 'powershell.exe' -or -not $taskAction.Arguments.Contains($expectedLauncher)) {
        throw "Refusing to stop unrelated task named $TaskName"
    }
    $configMatch = [regex]::Match($taskAction.Arguments, '-ConfigPath\s+"([^"]+)"')
    $pythonMatch = [regex]::Match($taskAction.Arguments, '-PythonPath\s+"([^"]+)"')
    if (-not $configMatch.Success -or -not $pythonMatch.Success) {
        throw 'Managed task arguments are incomplete'
    }
    $managedConfig = [IO.Path]::GetFullPath($configMatch.Groups[1].Value)
    $managedPython = [IO.Path]::GetFullPath($pythonMatch.Groups[1].Value)
    if (Test-Path -LiteralPath $managedConfig -PathType Leaf) {
        $priorPythonPath = $env:PYTHONPATH
        try {
            $env:PYTHONPATH = Join-Path $root 'src'
            & $managedPython -m mousse_controler.command_client --config $managedConfig stop 2>$null | Out-Null
        }
        finally {
            $env:PYTHONPATH = $priorPythonPath
        }
    }
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    $managed = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -like '*-m mousse_controler.app serve --config*' -and
            $_.CommandLine.Contains($managedConfig)
        })
    foreach ($process in $managed) {
        Stop-Process -Id $process.ProcessId -Force
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

if ($Action -eq 'Start') {
    if (-not $ConfigPath) { throw '-ConfigPath is required for Start' }
    $config = [IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { throw 'Controller config not found' }
    $old = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($old) {
        Stop-ManagedRuntime $old
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
        Stop-ManagedRuntime $task
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
