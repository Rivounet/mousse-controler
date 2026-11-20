[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('On', 'Off')]
    [string]$State,
    [Parameter(Mandatory)]
    [switch]$ConfirmStateChange,
    [switch]$NoRelaunch
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not $ConfirmStateChange) { throw 'Explicit -ConfirmStateChange is required' }
if ($PSVersionTable.PSEdition -eq 'Core' -and -not $NoRelaunch) {
    & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile `
        -ExecutionPolicy Bypass -File $PSCommandPath -State $State -ConfirmStateChange -NoRelaunch
    exit $LASTEXITCODE
}

function Convert-AsyncOperationToResult {
    param([Parameter(Mandatory)]$Operation, [Parameter(Mandatory)][Type]$ResultType)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(15000)) { throw 'WinRT operation timed out' }
    $task.Result
}

function Get-BluetoothRadio {
    $radios = Convert-AsyncOperationToResult `
        -Operation ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) `
        -ResultType ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
    $radios | Where-Object { $_.Kind.ToString() -eq 'Bluetooth' } | Select-Object -First 1
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
$radio = Get-BluetoothRadio
if (-not $radio) { throw 'Bluetooth radio was not enumerated' }
$initial = $radio.State.ToString()
if ($initial -ne $State) {
    $access = Convert-AsyncOperationToResult `
        -Operation ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) `
        -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
    if ($access.ToString() -ne 'Allowed') { throw "Radio access was not allowed: $access" }
    $requested = [Windows.Devices.Radios.RadioState]::$State
    $setResult = Convert-AsyncOperationToResult `
        -Operation ($radio.SetStateAsync($requested)) `
        -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
    if ($setResult.ToString() -ne 'Allowed') { throw "SetStateAsync($State) failed: $setResult" }
}
$deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    Start-Sleep -Milliseconds 200
    $radio = Get-BluetoothRadio
} while ($radio.State.ToString() -ne $State -and [DateTime]::UtcNow -lt $deadline)
$final = $radio.State.ToString()
[ordered]@{
    initial_state = $initial
    requested_state = $State
    final_state = $final
    confirmed = ($final -eq $State)
} | ConvertTo-Json
if ($final -ne $State) { exit 1 }
