$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
# Lecture de capacites uniquement : aucune publicite, aucun service GATT cree.
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$operation = [Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()
$method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$task = $method.MakeGenericMethod([Windows.Devices.Bluetooth.BluetoothAdapter]).Invoke($null,@($operation))
if (-not $task.Wait(15000)) { throw 'Timeout BluetoothAdapter.GetDefaultAsync' }
$adapter = $task.Result
if ($null -eq $adapter) { throw 'No default Bluetooth adapter returned' }
$adapter | Select-Object IsCentralRoleSupported,IsPeripheralRoleSupported,IsLowEnergySupported,IsClassicSupported | ConvertTo-Json
