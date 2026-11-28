[CmdletBinding()]
param(
    [switch]$NoRelaunch
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# PowerShell 7 does not project the WinRT metadata used below. Relaunch the
# exact same read-only diagnostic under the inbox Windows PowerShell runtime.
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
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } |
        Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutMilliseconds)) {
        throw "Timeout after ${TimeoutMilliseconds}ms while reading a WinRT capability"
    }
    return $task.Result
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$null = [Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]
$null = [Windows.Foundation.Metadata.ApiInformation,Windows.Foundation,ContentType=WindowsRuntime]

$adapter = Convert-AsyncOperationToResult `
    -Operation ([Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()) `
    -ResultType ([Windows.Devices.Bluetooth.BluetoothAdapter])
if ($null -eq $adapter) {
    throw 'No default Bluetooth adapter returned by Windows'
}
$adapterInformation = Convert-AsyncOperationToResult `
    -Operation ([Windows.Devices.Enumeration.DeviceInformation]::CreateFromIdAsync($adapter.DeviceId)) `
    -ResultType ([Windows.Devices.Enumeration.DeviceInformation])

$os = try { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop } catch { $null }
$currentVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$signedDriver = @(try { Get-CimInstance Win32_PnPSignedDriver -ErrorAction Stop } catch { @() }) |
    Where-Object { $_.DeviceClass -eq 'BLUETOOTH' -and $_.DeviceName -like '*Adapter*' } |
    Select-Object -First 1
if (-not $signedDriver) {
    $pnpAdapter = Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.FriendlyName -like '*Adapter*' } | Select-Object -First 1
    if ($pnpAdapter) {
        $driverVersion = Get-PnpDeviceProperty -InstanceId $pnpAdapter.InstanceId `
            -KeyName 'DEVPKEY_Device_DriverVersion' -ErrorAction SilentlyContinue
        $driverDate = Get-PnpDeviceProperty -InstanceId $pnpAdapter.InstanceId `
            -KeyName 'DEVPKEY_Device_DriverDate' -ErrorAction SilentlyContinue
        $manufacturer = Get-PnpDeviceProperty -InstanceId $pnpAdapter.InstanceId `
            -KeyName 'DEVPKEY_Device_Manufacturer' -ErrorAction SilentlyContinue
        $signedDriver = [pscustomobject]@{
            DeviceName = $pnpAdapter.FriendlyName
            Manufacturer = $manufacturer.Data
            DriverVersion = $driverVersion.Data
            DriverDate = $driverDate.Data
        }
    }
}
if (-not $signedDriver) {
    $signedDriver = [pscustomobject]@{
        DeviceName = $adapterInformation.Name
        Manufacturer = $null
        DriverVersion = $null
        DriverDate = $null
    }
}
$services = @(try { Get-Service -Name 'bthserv', 'BTAGService', 'BluetoothUserService*' -ErrorAction Stop } catch { @() }) |
    Sort-Object Name |
    ForEach-Object {
        [ordered]@{
            name = $_.Name -replace '_[0-9a-f]+$', '_<session>'
            status = $_.Status.ToString()
            start_type = $_.StartType.ToString()
        }
    }

$api = [Windows.Foundation.Metadata.ApiInformation]
$isWindowsIotCore =
    $currentVersion.EditionID -in @('IoTUAP', 'IoTCore') -or
    $currentVersion.ProductName -match 'IoT Core'
$inboundPairingRegistrationApi = $api::IsMethodPresent(
    'Windows.Devices.Enumeration.DeviceInformationPairing',
    'TryRegisterForAllInboundPairingRequests')
$codexCommand = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
$codexVersion = $null
if ($codexCommand) {
    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $codexOutput = (& codex --version 2>&1 | Out-String)
        if ($codexOutput -match 'codex-cli\s+[^\s]+') { $codexVersion = $Matches[0] }
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
}
$result = [ordered]@{
    schema = 1
    diagnostic_mode = 'read-only'
    machine = [ordered]@{
        expected_role = 'mini-pc-backend'
        name = $env:COMPUTERNAME.ToLowerInvariant()
        architecture = if ($os) { $os.OSArchitecture } elseif ([Environment]::Is64BitOperatingSystem) { '64-bit' } else { '32-bit' }
    }
    os = [ordered]@{
        caption = if ($os) { $os.Caption } else { $currentVersion.ProductName }
        version = if ($os) { $os.Version } else { [Environment]::OSVersion.Version.ToString() }
        build = "{0}.{1}" -f $currentVersion.CurrentBuildNumber, $currentVersion.UBR
        display_version = $currentVersion.DisplayVersion
        edition = $currentVersion.EditionID
    }
    runtimes = [ordered]@{
        powershell = $PSVersionTable.PSVersion.ToString()
        python = (& python --version 2>&1 | Out-String).Trim()
        git = (& git --version 2>&1 | Out-String).Trim()
        codex = $codexVersion
    }
    bluetooth = [ordered]@{
        adapter = [ordered]@{
            name = $signedDriver.DeviceName
            manufacturer = $signedDriver.Manufacturer
            driver_version = $signedDriver.DriverVersion
            driver_date = if ($signedDriver.DriverDate) { $signedDriver.DriverDate.ToString('yyyy-MM-dd') } else { $null }
        }
        capabilities = [ordered]@{
            central_role = $adapter.IsCentralRoleSupported
            peripheral_role = $adapter.IsPeripheralRoleSupported
            low_energy = $adapter.IsLowEnergySupported
            classic = $adapter.IsClassicSupported
        }
        winrt_api = [ordered]@{
            gatt_service_provider = $api::IsTypePresent('Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider')
            gatt_create_async = $api::IsMethodPresent('Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider', 'CreateAsync')
            gatt_start_advertising = $api::IsMethodPresent('Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider', 'StartAdvertising')
            local_characteristic = $api::IsTypePresent('Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristic')
            notify_value_async = $api::IsMethodPresent('Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristic', 'NotifyValueAsync')
            advertisement_publisher = $api::IsTypePresent('Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementPublisher')
            device_pairing = $api::IsTypePresent('Windows.Devices.Enumeration.DeviceInformationPairing')
            register_all_inbound_pairing_requests = $inboundPairingRegistrationApi
        }
        inbound_pairing = [ordered]@{
            platform_contract = 'Windows 10 IoT Core applications only'
            windows_iot_core = $isWindowsIotCore
            automatic_handler_implemented = $false
            unattended_supported = $false
            windows_desktop_requires_system_consent = -not $isWindowsIotCore
            reason = if ($isWindowsIotCore) {
                'No inbound pairing handler is implemented'
            } else {
                'Windows Desktop requires system consent for inbound pairing'
            }
        }
        services = @($services)
    }
    not_executed = @(
        'GATT service creation',
        'BLE advertising',
        'pairing',
        'HID report emission',
        'driver or Bluetooth configuration change'
    )
}

$result | ConvertTo-Json -Depth 6
