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

$result = [ordered]@{
    schema_version = 1
    device_name = $Name
    expected_id_sha256 = $ExpectedDeviceIdSha256.ToUpperInvariant()
    selected_id_sha256 = $null
    paired_aep_id_sha256 = $null
    initial_paired = $false
    pairing_status = 'NotAttempted'
    protection_level_used = 'Unverified'
    encryption_verified = $false
    pairing_rollback_status = 'NotRequired'
    paired = $false
    error_type = $null
    error_reason = $null
    session_id = [Diagnostics.Process]::GetCurrentProcess().SessionId
}
$device = $null
$exitCode = 0
$json = $null

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

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]
    $selector = 'System.Devices.Aep.ProtocolId:="{BB7BB05E-5972-42B5-94FC-76EAA7084D49}"'
    $properties = [System.Collections.Generic.List[string]]::new()
    $properties.Add('System.Devices.Aep.IsPaired')
    $properties.Add('System.Devices.Aep.DeviceAddress')
    $operation = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync(
        $selector, $properties, [Windows.Devices.Enumeration.DeviceInformationKind]::AssociationEndpoint)
    $devices = Convert-AsyncOperationToResult `
        -Operation $operation `
        -ResultType ([Windows.Devices.Enumeration.DeviceInformationCollection])
    $matches = @($devices | Where-Object { $_.Name -ceq $Name })
    $candidates = @($matches | ForEach-Object {
        $address = ([string]$_.Properties['System.Devices.Aep.DeviceAddress'] -replace '[:-]', '').ToUpperInvariant()
        if ($address -notmatch '^[0-9A-F]{12}$') { return }
        $identityBytes = [Text.Encoding]::ASCII.GetBytes($address)
        $sha256 = [Security.Cryptography.SHA256]::Create()
        try {
            $identity = ([BitConverter]::ToString($sha256.ComputeHash($identityBytes))).Replace('-', '')
        } finally {
            $sha256.Dispose()
            [Array]::Clear($identityBytes, 0, $identityBytes.Length)
        }
        [PSCustomObject]@{ Device = $_; IdSha256 = $identity }
    })
    $selected = @($candidates | Where-Object {
        $_.IdSha256 -ceq $result.expected_id_sha256
    } | Select-Object -First 1)
    if ($selected.Count -ne 1) {
        $result.error_type = 'ExactIdentityNotFound'
        throw 'No exact Bluetooth device matched the authorized physical identity.'
    }

    $result.selected_id_sha256 = $selected[0].IdSha256
    $device = $selected[0].Device
    $result.initial_paired = [bool]$device.Pairing.IsPaired
    if ($result.initial_paired) {
        $result.pairing_status = 'AlreadyPaired'
        $result.paired = $true
        $result.error_type = 'ExistingPairingUnverified'
        throw 'Existing pairing cannot prove the requested encryption; unpair it explicitly before qualification.'
    }

    $pairOperation = $device.Pairing.PairAsync(
        [Windows.Devices.Enumeration.DevicePairingProtectionLevel]::Encryption)
    $pairResult = Convert-AsyncOperationToResult `
        -Operation $pairOperation `
        -ResultType ([Windows.Devices.Enumeration.DevicePairingResult])
    $result.pairing_status = $pairResult.Status.ToString()
    $result.protection_level_used = $pairResult.ProtectionLevelUsed.ToString()

    if ($result.pairing_status -in @('Paired', 'AlreadyPaired') -and
        $result.protection_level_used -ne 'Encryption') {
        $result.error_type = 'RejectedProtectionLevel'
        try {
            $unpairOperation = $device.Pairing.UnpairAsync()
            $unpairResult = Convert-AsyncOperationToResult `
                -Operation $unpairOperation `
                -ResultType ([Windows.Devices.Enumeration.DeviceUnpairingResult])
            $result.pairing_rollback_status = $unpairResult.Status.ToString()
        } catch {
            $result.pairing_rollback_status = 'OperationFailed'
            throw "Pairing protection was '$($result.protection_level_used)' and rollback failed."
        }
        throw "Pairing protection was '$($result.protection_level_used)'; insecure pairing was rolled back with status '$($result.pairing_rollback_status)'."
    }

    $result.paired = [bool]$device.Pairing.IsPaired
    $result.encryption_verified = (
        $result.paired -and
        $result.pairing_status -in @('Paired', 'AlreadyPaired') -and
        $result.protection_level_used -eq 'Encryption'
    )
    if (-not $result.encryption_verified) {
        $result.error_type = 'PairingNotEncrypted'
        throw "Pairing did not establish an encrypted bond (status '$($result.pairing_status)')."
    }

    $pairedIdentityBytes = [Text.Encoding]::UTF8.GetBytes($device.Id)
    $pairedIdentitySha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $result.paired_aep_id_sha256 = ([BitConverter]::ToString(
            $pairedIdentitySha256.ComputeHash($pairedIdentityBytes))).Replace('-', '')
    } finally {
        $pairedIdentitySha256.Dispose()
        [Array]::Clear($pairedIdentityBytes, 0, $pairedIdentityBytes.Length)
    }
} catch {
    $exitCode = 1
    if ($null -eq $result.error_type) {
        $result.error_type = 'PairingOperationFailed'
    }
    $result.error_reason = $_.Exception.Message
} finally {
    if ($null -ne $device) {
        try { $result.paired = [bool]$device.Pairing.IsPaired } catch { }
    }
    $result.encryption_verified = (
        $result.paired -and
        $result.pairing_status -in @('Paired', 'AlreadyPaired') -and
        $result.protection_level_used -eq 'Encryption'
    )
    $resultDirectory = Split-Path -Parent $ResultPath
    if ($resultDirectory) {
        $null = New-Item -ItemType Directory -Path $resultDirectory -Force
    }
    $json = $result | ConvertTo-Json
    $temporaryResult = "$ResultPath.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        $json | Set-Content -LiteralPath $temporaryResult -Encoding UTF8
        Move-Item -LiteralPath $temporaryResult -Destination $ResultPath -Force
    } finally {
        Remove-Item -LiteralPath $temporaryResult -Force -ErrorAction SilentlyContinue
    }
}

$json
exit $exitCode
