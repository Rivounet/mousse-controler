[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedDeviceIdSha256,
    [Parameter(Mandatory)][switch]$ConfirmPairing,
    [Parameter(Mandatory)][string]$ResultPath,
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if (-not $ConfirmPairing) { throw 'Explicit -ConfirmPairing is required' }

function Convert-AsyncOperationToResult {
    param([Parameter(Mandatory)]$Operation, [Parameter(Mandatory)][Type]$ResultType)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutSeconds * 1000)) { throw 'Bluetooth operation timed out' }
    $task.Result
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]
$selector = 'System.Devices.Aep.ProtocolId:="{BB7BB05E-5972-42B5-94FC-76EAA7084D49}"'
$properties = [System.Collections.Generic.List[string]]::new()
$properties.Add('System.Devices.Aep.IsPaired')
$operation = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync(
    $selector, $properties, [Windows.Devices.Enumeration.DeviceInformationKind]::AssociationEndpoint)
$devices = Convert-AsyncOperationToResult `
    -Operation $operation `
    -ResultType ([Windows.Devices.Enumeration.DeviceInformationCollection])
$matches = @($devices | Where-Object { $_.Name -ceq $Name })
$candidates = @($matches | ForEach-Object {
    $identityBytes = [Text.Encoding]::UTF8.GetBytes($_.Id)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $identity = ([BitConverter]::ToString($sha256.ComputeHash($identityBytes))).Replace('-', '')
    } finally {
        $sha256.Dispose()
        [Array]::Clear($identityBytes, 0, $identityBytes.Length)
    }
    [PSCustomObject]@{ Device = $_; IdSha256 = $identity }
})
$expectedIdentity = $ExpectedDeviceIdSha256.ToUpperInvariant()
$selected = @($candidates | Where-Object { $_.IdSha256 -ceq $expectedIdentity })
if ($selected.Count -ne 1) {
    throw "Expected one exact Bluetooth device matching the authorized identity; found $($selected.Count)"
}
$device = $selected[0].Device
$initial = [bool]$device.Pairing.IsPaired
$protection = 'Unverified'
$rollbackStatus = 'NotRequired'
$status = 'AlreadyPaired'
if ($initial) {
    throw 'Existing pairing cannot prove the requested encryption; unpair it explicitly before qualification.'
}
else {
    $pairOperation = $device.Pairing.PairAsync(
        [Windows.Devices.Enumeration.DevicePairingProtectionLevel]::Encryption)
    $pairResult = Convert-AsyncOperationToResult `
        -Operation $pairOperation `
        -ResultType ([Windows.Devices.Enumeration.DevicePairingResult])
    $status = $pairResult.Status.ToString()
    $protection = $pairResult.ProtectionLevelUsed.ToString()
    if ($status -in @('Paired', 'AlreadyPaired') -and $protection -ne 'Encryption') {
        $unpairOperation = $device.Pairing.UnpairAsync()
        $unpairResult = Convert-AsyncOperationToResult `
            -Operation $unpairOperation `
            -ResultType ([Windows.Devices.Enumeration.DeviceUnpairingResult])
        $rollbackStatus = $unpairResult.Status.ToString()
        throw "Pairing protection was '$protection'; insecure pairing was rolled back with status '$rollbackStatus'."
    }
}
$result = [ordered]@{
    device_name = $Name
    expected_id_sha256 = $expectedIdentity
    selected_id_sha256 = $selected[0].IdSha256
    initial_paired = $initial
    pairing_status = $status
    protection_level_used = $protection
    encryption_verified = ($protection -eq 'Encryption')
    pairing_rollback_status = $rollbackStatus
    paired = [bool]$device.Pairing.IsPaired
    session_id = [Diagnostics.Process]::GetCurrentProcess().SessionId
}
$json = $result | ConvertTo-Json
$json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
$json
if (-not $result.paired -and $status -notin @('Paired', 'AlreadyPaired')) { exit 1 }
