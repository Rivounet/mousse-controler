[CmdletBinding()]
param([int]$TimeoutSeconds = 15)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Convert-AsyncOperationToResult {
    param([Parameter(Mandatory)]$Operation, [Parameter(Mandatory)][Type]$ResultType)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutSeconds * 1000)) { throw 'Bluetooth discovery timed out' }
    $task.Result
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]
$selector = 'System.Devices.Aep.ProtocolId:="{BB7BB05E-5972-42B5-94FC-76EAA7084D49}" AND System.Devices.Aep.IsPresent:=System.StructuredQueryType.Boolean#True'
$properties = [System.Collections.Generic.List[string]]::new()
$properties.Add('System.Devices.Aep.IsPaired')
$properties.Add('System.Devices.Aep.IsPresent')
$operation = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync(
    $selector, $properties, [Windows.Devices.Enumeration.DeviceInformationKind]::AssociationEndpoint)
$devices = Convert-AsyncOperationToResult `
    -Operation $operation `
    -ResultType ([Windows.Devices.Enumeration.DeviceInformationCollection])
$sha256 = [Security.Cryptography.SHA256]::Create()
@($devices | ForEach-Object {
    [ordered]@{
        name = $_.Name
        paired = [bool]$_.Pairing.IsPaired
        present = [bool]$_.Properties['System.Devices.Aep.IsPresent']
        id_sha256 = -join ($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($_.Id)) | ForEach-Object { $_.ToString('X2') })
    }
}) | ConvertTo-Json -Depth 4
$sha256.Dispose()
