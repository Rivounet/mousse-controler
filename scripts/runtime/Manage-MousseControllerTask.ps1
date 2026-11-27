[CmdletBinding()]
param(
    [Parameter(Mandatory, ParameterSetName = 'Execute')]
    [ValidateSet('Start', 'Status', 'Stop')][string]$Action,
    [string]$ConfigPath,
    [string]$ReleasePath,
    [string]$PythonPath = 'python.exe',
    [string]$TaskName = 'MousseControler-HOGP',
    [switch]$AllowLegacyTaskMigration,
    [Parameter(Mandatory, ParameterSetName = 'Library')]
    [Parameter(DontShow)][switch]$LibraryOnly
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'Start-MousseController.ps1'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Stop-ManagedRuntime($Task, [scriptblock]$EmergencyStopCommand, [bool]$AllowLegacyMigration = $false) {
    $taskAction = @($Task.Actions)[0]
    $launcherMatch = [regex]::Match($taskAction.Arguments, '-File\s+"([^"]+Start-MousseController\.ps1)"')
    if ($taskAction.Execute -ne 'powershell.exe' -or -not $launcherMatch.Success) {
        throw "Refusing to stop unrelated task named $TaskName"
    }
    $managedLauncher = [IO.Path]::GetFullPath($launcherMatch.Groups[1].Value)
    $managedRoot = [IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetDirectoryName($managedLauncher)) '..\..'))
    $managedManifest = Join-Path $managedRoot '.mousse-release.json'
    if ($managedLauncher -ne $launcher -and -not (Test-Path -LiteralPath $managedManifest -PathType Leaf)) {
        $workspaceRoot = [IO.Path]::GetDirectoryName([IO.Path]::GetDirectoryName($root))
        $legacyWorktrees = [IO.Path]::GetFullPath((Join-Path $workspaceRoot 'worktrees'))
        $managedParent = [IO.Path]::GetDirectoryName($managedRoot)
        if (-not $AllowLegacyMigration -or $managedParent -ne $legacyWorktrees) {
            throw "Refusing to stop task outside a managed controller release"
        }
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
            $env:PYTHONPATH = Join-Path $managedRoot 'src'
            try {
                if ($EmergencyStopCommand) {
                    & $EmergencyStopCommand $managedPython $managedConfig | Out-Null
                }
                else {
                    & $managedPython -m mousse_controler.command_client `
                        --config $managedConfig stop 2>$null | Out-Null
                }
            }
            catch {
                Write-Verbose "Controller emergency stop did not return cleanly: $($_.Exception.Message)"
            }
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

if ($LibraryOnly) { return }

if ($Action -eq 'Start') {
    if (-not $ConfigPath) { throw '-ConfigPath is required for Start' }
    if (-not $ReleasePath) { throw '-ReleasePath is required for Start' }
    $config = [IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { throw 'Controller config not found' }
    $release = [IO.Path]::GetFullPath($ReleasePath)
    $releaseLauncher = Join-Path $release 'scripts\runtime\Start-MousseController.ps1'
    $releaseVerifier = Join-Path $release 'scripts\runtime\controller_release.py'
    if (-not (Test-Path -LiteralPath $releaseLauncher -PathType Leaf) -or
        -not (Test-Path -LiteralPath $releaseVerifier -PathType Leaf)) {
        throw 'Controller release is incomplete'
    }
    & $PythonPath -B $releaseVerifier verify --release $release | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Controller release integrity verification failed' }
    $old = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($old) {
        Stop-ManagedRuntime $old $null $AllowLegacyTaskMigration
    }
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -ConfigPath "{1}" -PythonPath "{2}"' -f `
        $releaseLauncher, $config, $PythonPath
    $taskAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments `
        -WorkingDirectory ([IO.Path]::GetDirectoryName($releaseLauncher))
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
        -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
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
