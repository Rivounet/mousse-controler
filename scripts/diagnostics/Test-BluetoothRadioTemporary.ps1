[CmdletBinding()]
param(
    [Parameter(Mandatory)][switch]$ConfirmTemporaryActivation,
    [switch]$NoRelaunch
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not $ConfirmTemporaryActivation) {
    throw 'Explicit -ConfirmTemporaryActivation is required'
}

if ($PSVersionTable.PSEdition -eq 'Core' -and -not $NoRelaunch) {
    $windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath `
        -ConfirmTemporaryActivation -NoRelaunch
    exit $LASTEXITCODE
}

function Convert-AsyncOperationToResult {
    param(
        [Parameter(Mandatory)]$Operation,
        [Parameter(Mandatory)][Type]$ResultType,
        [int]$TimeoutMilliseconds = 15000
    )
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutMilliseconds)) { throw 'WinRT operation timed out' }
    return $task.Result
}

function Get-BluetoothRadio {
    $operation = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $radios = Convert-AsyncOperationToResult `
        -Operation $operation `
        -ResultType ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
    return $radios | Where-Object { $_.Kind.ToString() -eq 'Bluetooth' } | Select-Object -First 1
}

function Wait-RadioState {
    param(
        [Parameter(Mandatory)][string]$Expected,
        [int]$TimeoutMilliseconds = 15000
    )
    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    do {
        $current = Get-BluetoothRadio
        if ($current -and $current.State.ToString() -eq $Expected) { return $current }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    return Get-BluetoothRadio
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
$null = [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime]

$result = [ordered]@{
    schema = 1
    protocol = 'temporary Bluetooth radio activation with guaranteed restoration attempt'
    initial_state = $null
    request_access_status = $null
    set_on_status = $null
    confirmed_on = $false
    state_before_probe = $null
    gatt_probe = $null
    probe_process_exit_code = $null
    resources_released = $false
    set_off_status = $null
    final_state = $null
    restoration_confirmed = $false
    error = $null
    forbidden_operations = @('StartAdvertising', 'pairing', 'connection', 'notification', 'HID report')
}

$initialState = $null
$accessAllowed = $false
$exitCode = 0

try {
    $radio = Get-BluetoothRadio
    if (-not $radio) { throw 'Bluetooth radio was not enumerated' }
    $initialState = $radio.State.ToString()
    $result.initial_state = $initialState
    if ($initialState -ne 'Off') {
        throw "Expected initial Bluetooth state Off, observed $initialState"
    }

    $access = Convert-AsyncOperationToResult `
        -Operation ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) `
        -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
    $result.request_access_status = $access.ToString()
    $accessAllowed = ($access.ToString() -eq 'Allowed')
    if (-not $accessAllowed) { throw "Radio access was not allowed: $access" }

    $setOn = Convert-AsyncOperationToResult `
        -Operation ($radio.SetStateAsync([Windows.Devices.Radios.RadioState]::On)) `
        -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
    $result.set_on_status = $setOn.ToString()
    if ($setOn.ToString() -ne 'Allowed') { throw "SetStateAsync(On) was not allowed: $setOn" }

    $radio = Wait-RadioState -Expected 'On'
    $result.state_before_probe = if ($radio) { $radio.State.ToString() } else { $null }
    $result.confirmed_on = ($result.state_before_probe -eq 'On')
    if (-not $result.confirmed_on) { throw "Bluetooth did not reach On; observed $($result.state_before_probe)" }

    $probePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\bluetooth\probe-gatt-shape.ps1'))
    $probeOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $probePath
    $result.probe_process_exit_code = $LASTEXITCODE
    $result.resources_released = $true # Child process exited; WinRT references were released.
    if ($LASTEXITCODE -ne 0) { throw "GATT probe failed with exit code $LASTEXITCODE" }
    $result.gatt_probe = $probeOutput | Out-String | ConvertFrom-Json
} catch {
    $result.error = $_.Exception.Message
    $exitCode = 1
} finally {
    try {
        if ($initialState -eq 'Off') {
            $radio = Get-BluetoothRadio
            if ($radio -and $radio.State.ToString() -ne 'Off') {
                if (-not $accessAllowed) {
                    $access = Convert-AsyncOperationToResult `
                        -Operation ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) `
                        -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
                    $accessAllowed = ($access.ToString() -eq 'Allowed')
                }
                if (-not $accessAllowed) { throw 'Radio restoration access was not allowed' }
                $setOff = Convert-AsyncOperationToResult `
                    -Operation ($radio.SetStateAsync([Windows.Devices.Radios.RadioState]::Off)) `
                    -ResultType ([Windows.Devices.Radios.RadioAccessStatus])
                $result.set_off_status = $setOff.ToString()
            } else {
                $result.set_off_status = 'AlreadyOff'
            }
            $radio = Wait-RadioState -Expected 'Off'
            $result.final_state = if ($radio) { $radio.State.ToString() } else { $null }
            $result.restoration_confirmed = ($result.final_state -eq 'Off')
            if (-not $result.restoration_confirmed) {
                $exitCode = 1
                if (-not $result.error) { $result.error = 'Bluetooth restoration to Off was not confirmed' }
            }
        }
    } catch {
        $exitCode = 1
        $result.final_state = if ($radio) { $radio.State.ToString() } else { $null }
        $result.restoration_confirmed = ($result.final_state -eq 'Off')
        if (-not $result.error) { $result.error = "Restoration failed: $($_.Exception.Message)" }
    }
}

$result | ConvertTo-Json -Depth 12
exit $exitCode
