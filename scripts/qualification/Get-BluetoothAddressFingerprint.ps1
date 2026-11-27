[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if ($PSVersionTable.PSEdition -eq 'Core') {
    & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath
    exit $LASTEXITCODE
}

function Convert-AsyncOperationToResult {
    param(
        [Parameter(Mandatory)]$Operation,
        [Parameter(Mandatory)][Type]$ResultType
    )

    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(15000)) { throw 'BluetoothAdapter operation timed out' }
    $task.Result
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$adapterType = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$adapter = Convert-AsyncOperationToResult `
    -Operation ($adapterType::GetDefaultAsync()) `
    -ResultType $adapterType
if ($null -eq $adapter) { throw 'Default Bluetooth adapter was not found' }

$normalized = $adapter.BluetoothAddress.ToString('X12')
$clear = [Text.Encoding]::ASCII.GetBytes($normalized)
try {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = ([BitConverter]::ToString($algorithm.ComputeHash($clear))).Replace('-', '')
    }
    finally {
        $algorithm.Dispose()
    }
}
finally {
    [Array]::Clear($clear, 0, $clear.Length)
    $normalized = $null
}

[ordered]@{
    schema = 'mousse-bluetooth-address-fingerprint-v1'
    sha256 = $hash
    peripheral_role = [bool]$adapter.IsPeripheralRoleSupported
    central_role = [bool]$adapter.IsCentralRoleSupported
} | ConvertTo-Json -Compress
