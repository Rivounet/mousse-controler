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

function Invoke-Optional {
    param([Parameter(Mandatory)][scriptblock]$Operation)
    try { return & $Operation } catch { return $null }
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]

$radioList = Convert-AsyncOperationToResult `
    -Operation ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) `
    -ResultType ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$radios = @($radioList | ForEach-Object {
    [ordered]@{ kind = $_.Kind.ToString(); state = $_.State.ToString() }
})

$adapterWinRt = Convert-AsyncOperationToResult `
    -Operation ([Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()) `
    -ResultType ([Windows.Devices.Bluetooth.BluetoothAdapter])

$bluetoothDevices = @(Invoke-Optional { Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction Stop })
$adapter = $bluetoothDevices | Where-Object { $_.FriendlyName -like '*Adapter*' } | Select-Object -First 1
$properties = [ordered]@{}
if ($adapter) {
    foreach ($key in @(
        'DEVPKEY_Device_ProblemCode',
        'DEVPKEY_Device_ProblemStatus',
        'DEVPKEY_Device_DriverVersion',
        'DEVPKEY_Device_DriverDate',
        'DEVPKEY_Device_ConfigFlags'
    )) {
        $property = Get-PnpDeviceProperty -InstanceId $adapter.InstanceId -KeyName $key -ErrorAction SilentlyContinue
        $properties[$key.Replace('DEVPKEY_Device_', '').ToLowerInvariant()] = $property.Data
    }
}

$services = @('bthserv', 'BTAGService', 'RmSvc') | ForEach-Object {
    $serviceName = $_
    $service = Invoke-Optional { Get-Service -Name $serviceName -ErrorAction Stop }
    if ($service) {
        [ordered]@{
            name = $serviceName.ToLowerInvariant()
            status = $service.Status.ToString()
            start_type = $service.StartType.ToString()
        }
    }
}

$policyPaths = @(
    'HKLM:\SOFTWARE\Microsoft\PolicyManager\current\device\Bluetooth',
    'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Bluetooth'
)
$policyLocations = @($policyPaths | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
    $item = Get-ItemProperty -LiteralPath $_
    [ordered]@{
        scope = Split-Path $_ -Leaf
        configured_value_names = @($item.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object { $_.Name })
    }
})

$adapterEventGroups = @()
if ($adapter) {
    $events = @(Invoke-Optional {
        Get-WinEvent -FilterHashtable @{
            LogName = 'System'
            StartTime = (Get-Date).AddDays(-30)
            ProviderName = @('BTHUSB', 'BTHMINI', 'BTHLEENUM', 'Microsoft-Windows-Kernel-PnP')
        } -ErrorAction Stop
    })
    $escapedId = [System.Security.SecurityElement]::Escape($adapter.InstanceId)
    $adapterEventGroups = @($events |
        Where-Object { $_.ToXml() -like ('*' + $escapedId + '*') -and $_.Level -le 3 } |
        Group-Object ProviderName, Id, LevelDisplayName |
        ForEach-Object {
            [ordered]@{
                provider = $_.Group[0].ProviderName
                event_id = $_.Group[0].Id
                level = $_.Group[0].LevelDisplayName
                count = $_.Count
                last_utc = ($_.Group | Sort-Object TimeCreated -Descending | Select-Object -First 1).TimeCreated.ToUniversalTime().ToString('o')
            }
        })
}

$result = [ordered]@{
    schema = 1
    diagnostic_mode = 'read-only'
    radios = $radios
    bluetooth_adapter = [ordered]@{
        present = [bool]$adapter
        friendly_name = if ($adapter) { $adapter.FriendlyName } else { $null }
        pnp_status = if ($adapter) { $adapter.Status.ToString() } else { $null }
        properties = $properties
        low_energy_supported = if ($adapterWinRt) { $adapterWinRt.IsLowEnergySupported } else { $null }
        peripheral_role_supported = if ($adapterWinRt) { $adapterWinRt.IsPeripheralRoleSupported } else { $null }
    }
    bluetooth_present_device_count = $bluetoothDevices.Count
    bluetooth_problem_device_count = @($bluetoothDevices | Where-Object { $_.Status -ne 'OK' }).Count
    services = @($services)
    bluetooth_policy_locations = $policyLocations
    adapter_error_or_warning_events = $adapterEventGroups
    interpretation = [ordered]@{
        off_means_software_powered_off = @($radios | Where-Object { $_.kind -eq 'Bluetooth' -and $_.state -eq 'Off' }).Count -gt 0
        disabled_hardware_or_firmware_state_observed = @($radios | Where-Object { $_.kind -eq 'Bluetooth' -and $_.state -eq 'Disabled' }).Count -gt 0
    }
    not_executed = @(
        'Radio.RequestAccessAsync',
        'Radio.SetStateAsync',
        'GattServiceProvider.CreateAsync',
        'StartAdvertising',
        'pairing',
        'HID report emission',
        'driver, service, policy or Bluetooth configuration change'
    )
}

$result | ConvertTo-Json -Depth 8
