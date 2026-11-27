[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory)][string]$Address,
    [Parameter(Mandatory)][string]$ExpectedName,
    [ValidateRange(1, 60)][int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Wait-WinRtOperation {
    param(
        [Parameter(Mandatory)]$Operation,
        [Parameter(Mandatory)][Type]$ResultType
    )

    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    if ($null -eq $method) { throw 'Unable to locate the WinRT AsTask adapter.' }

    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutSeconds * 1000)) {
        try { $Operation.Cancel() } catch {}
        throw "Bluetooth operation timed out after $TimeoutSeconds seconds."
    }
    $task.GetAwaiter().GetResult()
}

$normalized = ($Address -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
if ($normalized -notmatch '^[0-9A-F]{12}$') {
    throw 'Address must contain exactly 12 hexadecimal digits.'
}
if ([string]::IsNullOrWhiteSpace($ExpectedName)) {
    throw 'ExpectedName must not be empty.'
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$deviceType = [Windows.Devices.Bluetooth.BluetoothLEDevice, Windows, ContentType=WindowsRuntime]
$unpairingResultType = [Windows.Devices.Enumeration.DeviceUnpairingResult, Windows, ContentType=WindowsRuntime]
$device = $null
try {
    $numericAddress = [Convert]::ToUInt64($normalized, 16)
    $device = Wait-WinRtOperation `
        -Operation ($deviceType::FromBluetoothAddressAsync($numericAddress)) `
        -ResultType $deviceType
    if ($null -eq $device) { throw 'The expected Bluetooth LE device was not found in the system cache.' }

    $actualName = [string]$device.Name
    if (-not $actualName.Equals($ExpectedName, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The resolved Bluetooth device name does not match ExpectedName; no change was made.'
    }

    $pairing = $device.DeviceInformation.Pairing
    if (-not $pairing.IsPaired) {
        [ordered]@{
            event = 'bluetooth-unpair'
            ok = $true
            status = 'AlreadyUnpaired'
            expected_name_matched = $true
        } | ConvertTo-Json -Compress
        exit 0
    }

    if (-not $PSCmdlet.ShouldProcess($ExpectedName, 'Unpair Bluetooth device')) {
        [ordered]@{
            event = 'bluetooth-unpair'
            ok = $true
            status = 'WhatIf'
            expected_name_matched = $true
        } | ConvertTo-Json -Compress
        exit 0
    }

    $result = Wait-WinRtOperation -Operation ($pairing.UnpairAsync()) -ResultType $unpairingResultType
    $status = [string]$result.Status
    if ($status -notin @('Unpaired', 'AlreadyUnpaired')) {
        throw "Bluetooth unpair failed with status $status."
    }
    [ordered]@{
        event = 'bluetooth-unpair'
        ok = $true
        status = $status
        expected_name_matched = $true
    } | ConvertTo-Json -Compress
}
finally {
    if ($null -ne $device -and $device -is [IDisposable]) { $device.Dispose() }
}
