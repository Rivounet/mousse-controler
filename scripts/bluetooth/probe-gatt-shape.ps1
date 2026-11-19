[CmdletBinding()]
param(
    [switch]$NoRelaunch
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if ($PSVersionTable.PSEdition -eq 'Core' -and -not $NoRelaunch) {
    $windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -NoRelaunch
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

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider,Windows.Devices.Bluetooth.GenericAttributeProfile,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicParameters,Windows.Devices.Bluetooth.GenericAttributeProfile,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalDescriptorParameters,Windows.Devices.Bluetooth.GenericAttributeProfile,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]

function New-ServiceProbe {
    param([Parameter(Mandatory)][Guid]$Uuid, [switch]$WithHidShape)

    $providerResult = Convert-AsyncOperationToResult `
        -Operation ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider]::CreateAsync($Uuid)) `
        -ResultType ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProviderResult])
    $entry = [ordered]@{
        uuid = $Uuid.ToString()
        provider_error = $providerResult.Error.ToString()
        provider_created = ($null -ne $providerResult.ServiceProvider)
        advertising_called = $false
        characteristics = @()
    }
    if (-not $entry.provider_created -or -not $WithHidShape) { return $entry }

    $definitions = @(
        @{ name = 'HID Information'; uuid = [Guid]'00002a4a-0000-1000-8000-00805f9b34fb'; props = 2 },
        @{ name = 'Report Map'; uuid = [Guid]'00002a4b-0000-1000-8000-00805f9b34fb'; props = 2 },
        @{ name = 'HID Control Point'; uuid = [Guid]'00002a4c-0000-1000-8000-00805f9b34fb'; props = 4 },
        @{ name = 'Input Report'; uuid = [Guid]'00002a4d-0000-1000-8000-00805f9b34fb'; props = 18 }
    )
    foreach ($definition in $definitions) {
        $parameters = New-Object Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicParameters
        $parameters.CharacteristicProperties = $definition.props
        $parameters.ReadProtectionLevel = 2 # EncryptionRequired
        $parameters.WriteProtectionLevel = 2
        $created = Convert-AsyncOperationToResult `
            -Operation ($providerResult.ServiceProvider.Service.CreateCharacteristicAsync($definition.uuid, $parameters)) `
            -ResultType ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicResult])
        $characteristic = [ordered]@{
            name = $definition.name
            error = $created.Error.ToString()
            created = ($null -ne $created.Characteristic)
        }
        if ($definition.name -eq 'Input Report' -and $characteristic.created) {
            $descriptorParameters = New-Object Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalDescriptorParameters
            $descriptorParameters.ReadProtectionLevel = 2
            $descriptorParameters.StaticValue = `
                [System.Runtime.InteropServices.WindowsRuntime.WindowsRuntimeBufferExtensions]::AsBuffer(
                    [byte[]](0, 1) # Report ID 0, Input Report type 1
                )
            $descriptor = Convert-AsyncOperationToResult `
                -Operation ($created.Characteristic.CreateDescriptorAsync([Guid]'00002908-0000-1000-8000-00805f9b34fb', $descriptorParameters)) `
                -ResultType ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalDescriptorResult])
            $characteristic.report_reference_descriptor = [ordered]@{
                error = $descriptor.Error.ToString()
                created = ($null -ne $descriptor.Descriptor)
            }
        }
        $entry.characteristics += $characteristic
    }
    return $entry
}

$adapter = Convert-AsyncOperationToResult `
    -Operation ([Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()) `
    -ResultType ([Windows.Devices.Bluetooth.BluetoothAdapter])
$radio = if ($adapter) {
    Convert-AsyncOperationToResult -Operation ($adapter.GetRadioAsync()) -ResultType ([Windows.Devices.Radios.Radio])
} else { $null }

$result = [ordered]@{
    schema = 1
    probe_mode = 'ephemeral WinRT object creation; never advertised'
    adapter = [ordered]@{
        present = ($null -ne $adapter)
        peripheral_role_supported = if ($adapter) { $adapter.IsPeripheralRoleSupported } else { $null }
        radio_state = if ($radio) { $radio.State.ToString() } else { $null }
    }
    hid_service = New-ServiceProbe -Uuid ([Guid]'00001812-0000-1000-8000-00805f9b34fb') -WithHidShape
    battery_service = New-ServiceProbe -Uuid ([Guid]'0000180f-0000-1000-8000-00805f9b34fb')
    device_information_reserved_service = New-ServiceProbe -Uuid ([Guid]'0000180a-0000-1000-8000-00805f9b34fb')
    not_executed = @('StartAdvertising', 'pairing', 'connection', 'notification', 'HID report')
}

$result | ConvertTo-Json -Depth 8
