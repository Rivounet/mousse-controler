[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
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
if ($matches.Count -ne 1) { throw "Expected one exact Bluetooth device named '$Name'; found $($matches.Count)" }
$device = $matches[0]
$initial = [bool]$device.Pairing.IsPaired
$status = 'AlreadyPaired'
if (-not $initial) {
    $pairOperation = $device.Pairing.PairAsync(
        [Windows.Devices.Enumeration.DevicePairingProtectionLevel]::Encryption)
    $pairResult = Convert-AsyncOperationToResult `
        -Operation $pairOperation `
        -ResultType ([Windows.Devices.Enumeration.DevicePairingResult])
    $status = $pairResult.Status.ToString()
}
$result = [ordered]@{
    device_name = $Name
    initial_paired = $initial
    pairing_status = $status
    paired = [bool]$device.Pairing.IsPaired
    session_id = [Diagnostics.Process]::GetCurrentProcess().SessionId
}
$json = $result | ConvertTo-Json
$json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
$json
if (-not $result.paired -and $status -notin @('Paired', 'AlreadyPaired')) { exit 1 }
