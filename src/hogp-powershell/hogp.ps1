param([switch]$Stdio)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

if (-not $Stdio) {
    [Console]::Error.WriteLine('Usage: hogp.ps1 --stdio')
    exit 2
}

function Wait-WinRtOperation {
    param(
        [Parameter(Mandatory)]$Operation,
        [Parameter(Mandatory)][Type]$ResultType,
        [ValidateRange(1, 60000)][int]$TimeoutMilliseconds = 5000
    )

    $asTaskMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    if ($null -eq $asTaskMethod) {
        throw 'Unable to locate the WinRT AsTask adapter.'
    }
    $task = $asTaskMethod.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait($TimeoutMilliseconds)) {
        try { $Operation.Cancel() } catch {}
        throw [TimeoutException]::new("WinRT operation timed out after $TimeoutMilliseconds ms")
    }
    $task.GetAwaiter().GetResult()
}

function Write-Event {
    param(
        [Parameter(Mandatory)][string]$Event,
        [Parameter(Mandatory)][bool]$Ok,
        [string]$Detail
    )

    $message = [ordered]@{ event = $Event; ok = $Ok }
    if ($Detail) { $message.detail = $Detail }
    [Console]::Out.WriteLine(($message | ConvertTo-Json -Compress))
    [Console]::Out.Flush()
}

function New-Buffer {
    param([Parameter(Mandatory)][byte[]]$Bytes)

    $bufferType = [Windows.Security.Cryptography.CryptographicBuffer, Windows, ContentType=WindowsRuntime]
    $bufferType::CreateFromByteArray($Bytes)
}

function New-StaticParameters {
    param(
        [Parameter(Mandatory)]$Properties,
        [Parameter(Mandatory)][byte[]]$Value
    )

    $parametersType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicParameters, Windows, ContentType=WindowsRuntime]
    $protectionType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattProtectionLevel, Windows, ContentType=WindowsRuntime]
    $parameters = $parametersType::new()
    $parameters.CharacteristicProperties = $Properties
    $parameters.ReadProtectionLevel = $protectionType::EncryptionRequired
    $parameters.WriteProtectionLevel = $protectionType::EncryptionRequired
    # Windows PowerShell exposes IBuffer values as __ComObject. Its normal
    # property binder cannot cast that RCW back to IBuffer, while the CLR
    # property setter can consume it directly.
    $parametersType.GetProperty('StaticValue').SetValue($parameters, (New-Buffer $Value))
    $parameters
}

function New-Characteristic {
    param(
        [Parameter(Mandatory)]$Provider,
        [Parameter(Mandatory)][Guid]$Uuid,
        [Parameter(Mandatory)]$Parameters,
        [Parameter(Mandatory)][string]$Name
    )

    $resultType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicResult, Windows, ContentType=WindowsRuntime]
    $result = Wait-WinRtOperation ($Provider.Service.CreateCharacteristicAsync($Uuid, $Parameters)) $resultType
    if ([string]$result.Error -ne 'Success' -or $null -eq $result.Characteristic) {
        throw "$Name creation failed: $($result.Error)"
    }
    $result.Characteristic
}

function Test-AdvertisingStatus {
    param($Status)
    $name = [string]$Status
    $name -eq 'Started' -or $name -eq 'StartedWithoutAllAdvertisementData'
}

function Stop-AdvertisingAndWait {
    param([Parameter(Mandatory)]$Provider)

    if (-not (Test-AdvertisingStatus $Provider.AdvertisementStatus)) { return }
    $Provider.StopAdvertising()
    $deadline = [DateTime]::UtcNow.AddSeconds(3)
    while ((Test-AdvertisingStatus $Provider.AdvertisementStatus) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 20
    }
    if (Test-AdvertisingStatus $Provider.AdvertisementStatus) {
        throw "advertising did not stop; status=$($Provider.AdvertisementStatus)"
    }
}

function New-ReportBuffer {
    param(
        [ValidateRange(0, 31)][int]$Buttons,
        [ValidateRange(-32768, 32767)][int]$Dx,
        [ValidateRange(-32768, 32767)][int]$Dy,
        [ValidateRange(-127, 127)][int]$Wheel
    )

    $dxUnsigned = [uint16]($Dx -band 0xffff)
    $dyUnsigned = [uint16]($Dy -band 0xffff)
    New-Buffer ([byte[]]@(
        [byte]$Buttons,
        [byte]($dxUnsigned -band 0xff), [byte](($dxUnsigned -shr 8) -band 0xff),
        [byte]($dyUnsigned -band 0xff), [byte](($dyUnsigned -shr 8) -band 0xff),
        [byte]($Wheel -band 0xff)
    ))
}

function Send-Report {
    param(
        [ValidateRange(0, 31)][int]$Buttons,
        [ValidateRange(-32768, 32767)][int]$Dx,
        [ValidateRange(-32768, 32767)][int]$Dy,
        [ValidateRange(-127, 127)][int]$Wheel
    )

    if ($null -eq $script:InputReport -or $script:InputReport.SubscribedClients.Count -eq 0) {
        throw 'no subscribed HID host'
    }
    $resultItemType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattClientNotificationResult, Windows, ContentType=WindowsRuntime]
    $resultType = [System.Collections.Generic.IReadOnlyList``1].MakeGenericType($resultItemType)
    $bufferType = [Windows.Storage.Streams.IBuffer, Windows, ContentType=WindowsRuntime]
    $notifyMethod = $script:InputReport.GetType().GetMethod(
        'NotifyValueAsync', [Type[]]@($bufferType))
    if ($null -eq $notifyMethod) {
        throw 'Unable to locate the one-buffer NotifyValueAsync overload.'
    }
    $reportBuffer = New-ReportBuffer $Buttons $Dx $Dy $Wheel
    $operation = $notifyMethod.Invoke($script:InputReport, @($reportBuffer))
    $results = Wait-WinRtOperation $operation $resultType
    if ($null -eq $results -or $results.Count -eq 0) {
        throw 'notification reached no clients'
    }
    foreach ($result in $results) {
        if ([string]$result.Status -ne 'Success') {
            throw "notification status: $($result.Status)"
        }
    }
    Write-Event 'report' $true
}

function Stop-Hogp {
    if ($null -ne $script:HidProvider -and (Test-AdvertisingStatus $script:HidProvider.AdvertisementStatus)) {
        try { Stop-AdvertisingAndWait $script:HidProvider } catch {}
    }
    $script:Buttons = 0
    $script:InputReport = $null
    $script:BatteryProvider = $null
    $script:HidProvider = $null
}

$script:HidProvider = $null
$script:BatteryProvider = $null
$script:InputReport = $null
$script:Buttons = 0

try {
    $adapterType = [Windows.Devices.Bluetooth.BluetoothAdapter, Windows, ContentType=WindowsRuntime]
    $adapter = Wait-WinRtOperation ($adapterType::GetDefaultAsync()) $adapterType
    if ($null -eq $adapter -or -not $adapter.IsPeripheralRoleSupported) {
        throw 'Bluetooth peripheral role unavailable'
    }

    $providerResultType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProviderResult, Windows, ContentType=WindowsRuntime]
    $providerType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider, Windows, ContentType=WindowsRuntime]
    $hidResult = Wait-WinRtOperation ($providerType::CreateAsync([Guid]'00001812-0000-1000-8000-00805f9b34fb')) $providerResultType
    if ([string]$hidResult.Error -ne 'Success' -or $null -eq $hidResult.ServiceProvider) {
        throw "HID provider creation failed: $($hidResult.Error)"
    }
    $script:HidProvider = $hidResult.ServiceProvider

    $propertiesType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattCharacteristicProperties, Windows, ContentType=WindowsRuntime]
    $null = New-Characteristic $script:HidProvider ([Guid]'00002a4a-0000-1000-8000-00805f9b34fb') `
        (New-StaticParameters $propertiesType::Read ([byte[]]@(0x11, 0x01, 0x00, 0x02))) 'HID Information'
    $reportMap = [byte[]]@(
        0x05,0x01,0x09,0x02,0xA1,0x01,0x09,0x01,0xA1,0x00,
        0x05,0x09,0x19,0x01,0x29,0x05,0x15,0x00,0x25,0x01,
        0x95,0x05,0x75,0x01,0x81,0x02,0x95,0x01,0x75,0x03,
        0x81,0x03,0x05,0x01,0x09,0x30,0x09,0x31,0x16,0x00,
        0x80,0x26,0xFF,0x7F,0x75,0x10,0x95,0x02,0x81,0x06,
        0x09,0x38,0x15,0x81,0x25,0x7F,0x75,0x08,0x95,0x01,
        0x81,0x06,0xC0,0xC0
    )
    $null = New-Characteristic $script:HidProvider ([Guid]'00002a4b-0000-1000-8000-00805f9b34fb') `
        (New-StaticParameters $propertiesType::Read $reportMap) 'Report Map'

    $parametersType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalCharacteristicParameters, Windows, ContentType=WindowsRuntime]
    $protectionType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattProtectionLevel, Windows, ContentType=WindowsRuntime]
    $controlParameters = $parametersType::new()
    $controlParameters.CharacteristicProperties = $propertiesType::WriteWithoutResponse
    $controlParameters.ReadProtectionLevel = $protectionType::EncryptionRequired
    $controlParameters.WriteProtectionLevel = $protectionType::EncryptionRequired
    $null = New-Characteristic $script:HidProvider ([Guid]'00002a4c-0000-1000-8000-00805f9b34fb') `
        $controlParameters 'HID Control Point'

    $reportProperties = [enum]::ToObject($propertiesType, ([int]$propertiesType::Read -bor [int]$propertiesType::Notify))
    $reportParameters = New-StaticParameters $reportProperties ([byte[]]@(0, 0, 0, 0, 0, 0))
    $script:InputReport = New-Characteristic $script:HidProvider ([Guid]'00002a4d-0000-1000-8000-00805f9b34fb') `
        $reportParameters 'Input Report'

    $descriptorParametersType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalDescriptorParameters, Windows, ContentType=WindowsRuntime]
    $descriptorParameters = $descriptorParametersType::new()
    $descriptorParameters.ReadProtectionLevel = $protectionType::EncryptionRequired
    $descriptorParametersType.GetProperty('StaticValue').SetValue(
        $descriptorParameters, (New-Buffer ([byte[]]@(0x00, 0x01))))
    $descriptorResultType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattLocalDescriptorResult, Windows, ContentType=WindowsRuntime]
    $descriptorResult = Wait-WinRtOperation `
        ($script:InputReport.CreateDescriptorAsync([Guid]'00002908-0000-1000-8000-00805f9b34fb', $descriptorParameters)) `
        $descriptorResultType
    if ([string]$descriptorResult.Error -ne 'Success' -or $null -eq $descriptorResult.Descriptor) {
        throw "Report Reference creation failed: $($descriptorResult.Error)"
    }

    $batteryResult = Wait-WinRtOperation ($providerType::CreateAsync([Guid]'0000180f-0000-1000-8000-00805f9b34fb')) $providerResultType
    if ([string]$batteryResult.Error -ne 'Success' -or $null -eq $batteryResult.ServiceProvider) {
        throw "Battery provider creation failed: $($batteryResult.Error)"
    }
    $script:BatteryProvider = $batteryResult.ServiceProvider
    $null = New-Characteristic $script:BatteryProvider ([Guid]'00002a19-0000-1000-8000-00805f9b34fb') `
        (New-StaticParameters $propertiesType::Read ([byte[]]@(100))) 'Battery Level'

    Write-Event 'prepared' $true 'HID and Battery services created; advertising stopped'

    while (($line = [Console]::In.ReadLine()) -ne $null) {
        try {
            $parts = @($line.Trim() -split '\s+')
            if ($parts.Count -eq 0 -or -not $parts[0]) { continue }
            switch ($parts[0]) {
                'status' {
                    $subscribed = $null -ne $script:InputReport -and $script:InputReport.SubscribedClients.Count -gt 0
                    Write-Event 'status' $true "prepared=True,advertising=$(Test-AdvertisingStatus $script:HidProvider.AdvertisementStatus),advertisement_status=$($script:HidProvider.AdvertisementStatus),subscribed=$subscribed,buttons=$script:Buttons"
                }
                'advertise' {
                    if ($parts.Count -ne 2 -or $parts[1] -notin @('start', 'pairable', 'stop')) {
                        throw 'advertise expects start, pairable or stop'
                    }
                    if ($parts[1] -eq 'stop') {
                        Stop-AdvertisingAndWait $script:HidProvider
                        Write-Event 'advertise-stop' $true ([string]$script:HidProvider.AdvertisementStatus)
                        break
                    }
                    $advertisingParametersType = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProviderAdvertisingParameters, Windows, ContentType=WindowsRuntime]
                    $advertisingParameters = $advertisingParametersType::new()
                    $advertisingParameters.IsConnectable = $true
                    # This Windows provider only reaches Started with discoverable
                    # advertising on the qualified adapter. Incoming pairing is
                    # still gated separately by the bounded OS pairability window.
                    $advertisingParameters.IsDiscoverable = $true
                    $script:HidProvider.StartAdvertising($advertisingParameters)
                    $deadline = [DateTime]::UtcNow.AddSeconds(3)
                    while (-not (Test-AdvertisingStatus $script:HidProvider.AdvertisementStatus) -and [DateTime]::UtcNow -lt $deadline) {
                        Start-Sleep -Milliseconds 20
                    }
                    if (-not (Test-AdvertisingStatus $script:HidProvider.AdvertisementStatus)) {
                        throw "advertising did not start; status=$($script:HidProvider.AdvertisementStatus)"
                    }
                    $mode = if ($parts[1] -eq 'pairable') { 'pairable' } else { 'connectable' }
                    Write-Event 'advertise-start' $true "$($script:HidProvider.AdvertisementStatus);mode=$mode"
                }
                'move' {
                    if ($parts.Count -ne 3) { throw 'move expects dx and dy' }
                    Send-Report $script:Buttons ([int]$parts[1]) ([int]$parts[2]) 0
                }
                'scroll' {
                    if ($parts.Count -ne 2) { throw 'scroll expects delta' }
                    Send-Report $script:Buttons 0 0 ([int]$parts[1])
                }
                'buttons' {
                    if ($parts.Count -ne 2) { throw 'buttons expects mask' }
                    $mask = [int]$parts[1]
                    Send-Report $mask 0 0 0
                    $script:Buttons = $mask
                }
                'release' {
                    if ($script:InputReport.SubscribedClients.Count -gt 0) {
                        Send-Report 0 0 0 0
                    }
                    $script:Buttons = 0
                    Write-Event 'release' $true
                }
                'stop' {
                    if ($script:InputReport.SubscribedClients.Count -gt 0) {
                        try { Send-Report 0 0 0 0 } catch {}
                    }
                    Stop-Hogp
                    Write-Event 'stopped' $true
                    exit 0
                }
                default { throw 'unknown command' }
            }
        }
        catch {
            Write-Event 'command' $false $_.Exception.Message
        }
    }
}
catch {
    Write-Event 'fatal' $false $_.Exception.Message
    Stop-Hogp
    exit 1
}
finally {
    Stop-Hogp
}
