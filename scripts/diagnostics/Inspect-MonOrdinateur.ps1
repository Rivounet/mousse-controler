[CmdletBinding()]
param(
    [string]$MiniPcHost,
    [ValidateRange(1, 65535)][int]$MiniPcPort = 443,
    [switch]$NoRelaunch
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# PowerShell 7 does not expose the WinRT projection used below. Relaunch the
# same read-only inventory under inbox Windows PowerShell when necessary.
if ($PSVersionTable.PSEdition -eq 'Core' -and -not $NoRelaunch) {
    $windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath, '-NoRelaunch', '-MiniPcPort', $MiniPcPort)
    if ($MiniPcHost) { $arguments += @('-MiniPcHost', $MiniPcHost) }
    & $windowsPowerShell @arguments
    exit $LASTEXITCODE
}

# The result deliberately omits users, host names, addresses, adapter IDs and
# firewall rules. No API below changes a setting or emits input.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class MouseControlAuditNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool GetCursorPos(out POINT point);

    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool GetPhysicalCursorPos(out POINT point);

    [DllImport("user32.dll")]
    public static extern int GetSystemMetrics(int index);

    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool SystemParametersInfo(uint action, uint param, int[] value, uint flags);

    [DllImport("user32.dll")]
    public static extern IntPtr GetThreadDpiAwarenessContext();

    [DllImport("user32.dll")]
    public static extern uint GetDpiForSystem();

    [DllImport("kernel32.dll")]
    public static extern uint WTSGetActiveConsoleSessionId();

    [DllImport("user32.dll", SetLastError=true)]
    public static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint desiredAccess);

    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool CloseDesktop(IntPtr desktop);

    [DllImport("user32.dll")]
    public static extern IntPtr MonitorFromPoint(POINT point, uint flags);

    [DllImport("shcore.dll")]
    public static extern int GetDpiForMonitor(IntPtr monitor, int dpiType, out uint dpiX, out uint dpiY);
}
'@

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

function Get-CommandVersion {
    param([Parameter(Mandatory)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) { return $null }
    return [ordered]@{
        available = $true
        version = if ($command.Version) { $command.Version.ToString() } else { $null }
    }
}

function Invoke-Optional {
    param([Parameter(Mandatory)][scriptblock]$Operation)
    try { return & $Operation } catch { return $null }
}

$cursor = New-Object MouseControlAuditNative+POINT
$cursorOk = [MouseControlAuditNative]::GetCursorPos([ref]$cursor)
$physicalCursor = New-Object MouseControlAuditNative+POINT
$physicalCursorOk = [MouseControlAuditNative]::GetPhysicalCursorPos([ref]$physicalCursor)
$inputDesktop = [MouseControlAuditNative]::OpenInputDesktop(0, $false, 1) # DESKTOP_READOBJECTS
$inputDesktopReadable = ($inputDesktop -ne [IntPtr]::Zero)
if ($inputDesktopReadable) { $null = [MouseControlAuditNative]::CloseDesktop($inputDesktop) }

$mouse = New-Object int[] 3
$mouseOk = [MouseControlAuditNative]::SystemParametersInfo(3, 0, $mouse, 0) # SPI_GETMOUSE
$speed = New-Object int[] 1
$speedOk = [MouseControlAuditNative]::SystemParametersInfo(112, 0, $speed, 0) # SPI_GETMOUSESPEED

$dotNetRelease = $null
$dotNetVersion = $null
$dotNetKey = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue
if ($dotNetKey) {
    $dotNetRelease = $dotNetKey.Release
    $dotNetVersion = $dotNetKey.Version
}

$cscCandidates = @(
    (Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'),
    (Join-Path $env:SystemRoot 'Microsoft.NET\Framework\v4.0.30319\csc.exe')
)
$csc = $cscCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

$bluetoothDriver = Invoke-Optional { Get-CimInstance Win32_PnPSignedDriver -ErrorAction Stop } |
    Where-Object { $_.DeviceClass -eq 'BLUETOOTH' -and $_.DeviceName -like '*Adapter*' } |
    Select-Object -First 1
$bluetoothPnp = Invoke-Optional {
    Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction Stop |
        Where-Object { $_.FriendlyName -like '*Adapter*' } | Select-Object -First 1
}
$bluetoothProblemCode = $null
if ($bluetoothPnp) {
    $problem = Get-PnpDeviceProperty -InstanceId $bluetoothPnp.InstanceId `
        -KeyName 'DEVPKEY_Device_ProblemCode' -ErrorAction SilentlyContinue
    $bluetoothProblemCode = $problem.Data
}
$mouseDevices = @(Invoke-Optional { Get-PnpDevice -Class Mouse -PresentOnly -ErrorAction Stop } | Where-Object { $null -ne $_ })
$bluetoothServices = @('bthserv', 'BTAGService', 'RmSvc') | ForEach-Object {
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

$radioState = $null
$peripheralRole = $null
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
    $null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
    $adapter = Convert-AsyncOperationToResult `
        -Operation ([Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()) `
        -ResultType ([Windows.Devices.Bluetooth.BluetoothAdapter])
    if ($adapter) {
        $peripheralRole = $adapter.IsPeripheralRoleSupported
        $radio = Convert-AsyncOperationToResult `
            -Operation ($adapter.GetRadioAsync()) `
            -ResultType ([Windows.Devices.Radios.Radio])
        if ($radio) { $radioState = $radio.State.ToString() }
    }
} catch {
    $radioState = $null
}

$profiles = @(Invoke-Optional { Get-NetConnectionProfile -ErrorAction Stop } | Where-Object { $null -ne $_ } | ForEach-Object {
    [ordered]@{
        category = if ($null -ne $_.NetworkCategory) { $_.NetworkCategory.ToString() } else { $null }
        connectivity = if ($null -ne $_.IPv4Connectivity) { $_.IPv4Connectivity.ToString() } else { $null }
    }
})
$firewall = @(Invoke-Optional { Get-NetFirewallProfile -ErrorAction Stop } | Where-Object { $null -ne $_ } | Sort-Object Name | ForEach-Object {
    [ordered]@{
        profile = $_.Name
        enabled = $_.Enabled
        default_inbound_action = if ($null -ne $_.DefaultInboundAction) { $_.DefaultInboundAction.ToString() } else { $null }
        default_outbound_action = if ($null -ne $_.DefaultOutboundAction) { $_.DefaultOutboundAction.ToString() } else { $null }
    }
})

$screens = @([System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
    $center = New-Object MouseControlAuditNative+POINT
    $center.X = $_.Bounds.Left + [int]($_.Bounds.Width / 2)
    $center.Y = $_.Bounds.Top + [int]($_.Bounds.Height / 2)
    $monitor = [MouseControlAuditNative]::MonitorFromPoint($center, 2) # MONITOR_DEFAULTTONEAREST
    [uint32]$dpiX = 0
    [uint32]$dpiY = 0
    $dpiResult = if ($monitor -ne [IntPtr]::Zero) {
        [MouseControlAuditNative]::GetDpiForMonitor($monitor, 0, [ref]$dpiX, [ref]$dpiY) # MDT_EFFECTIVE_DPI
    } else { -1 }
    [ordered]@{
        primary = $_.Primary
        bounds = [ordered]@{
            left = $_.Bounds.Left
            top = $_.Bounds.Top
            width = $_.Bounds.Width
            height = $_.Bounds.Height
        }
        effective_dpi = if ($dpiResult -eq 0) { [ordered]@{ x = $dpiX; y = $dpiY } } else { $null }
    }
})

$tcpProbe = $null
if ($MiniPcHost) {
    $tcpProbe = Invoke-Optional {
        Test-NetConnection -ComputerName $MiniPcHost -Port $MiniPcPort `
            -InformationLevel Quiet -WarningAction SilentlyContinue
    }
}

$osCim = Invoke-Optional { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop }
$currentVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'

$result = [ordered]@{
    schema = 2
    diagnostic_mode = 'read-only'
    intended_machine_role = 'Windows HID target and position-feedback agent'
    os = [ordered]@{
        caption = if ($osCim) { $osCim.Caption } else { $currentVersion.ProductName }
        version = [Environment]::OSVersion.Version.ToString()
        build = "{0}.{1}" -f $currentVersion.CurrentBuildNumber, $currentVersion.UBR
        architecture = if ($osCim) { $osCim.OSArchitecture } elseif ([Environment]::Is64BitOperatingSystem) { '64-bit' } else { '32-bit' }
        process_is_64_bit = [Environment]::Is64BitProcess
    }
    runtime = [ordered]@{
        powershell = $PSVersionTable.PSVersion.ToString()
        dotnet_cli = Get-CommandVersion -Name 'dotnet'
        dotnet_framework_full = [ordered]@{ version = $dotNetVersion; release = $dotNetRelease }
        inbox_csharp_compiler = [ordered]@{
            available = [bool]$csc
            framework = if ($csc) { if ($csc -like '*Framework64*') { 'Framework64' } else { 'Framework' } } else { $null }
        }
    }
    session = [ordered]@{
        process_session_id = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
        active_console_session_id = [MouseControlAuditNative]::WTSGetActiveConsoleSessionId()
        interactive = [Environment]::UserInteractive
        input_desktop_readable = $inputDesktopReadable
    }
    cursor = [ordered]@{
        get_cursor_pos_succeeded = $cursorOk
        position = if ($cursorOk) { [ordered]@{ x = $cursor.X; y = $cursor.Y } } else { $null }
        get_physical_cursor_pos_succeeded = $physicalCursorOk
        logical_matches_physical = if ($cursorOk -and $physicalCursorOk) {
            ($cursor.X -eq $physicalCursor.X -and $cursor.Y -eq $physicalCursor.Y)
        } else { $null }
        virtual_screen = [ordered]@{
            left = [MouseControlAuditNative]::GetSystemMetrics(76)
            top = [MouseControlAuditNative]::GetSystemMetrics(77)
            width = [MouseControlAuditNative]::GetSystemMetrics(78)
            height = [MouseControlAuditNative]::GetSystemMetrics(79)
        }
        monitors = $screens
        system_dpi = [MouseControlAuditNative]::GetDpiForSystem()
        thread_dpi_awareness_context_nonzero = ([MouseControlAuditNative]::GetThreadDpiAwarenessContext() -ne [IntPtr]::Zero)
        pointer_settings = [ordered]@{
            query_succeeded = ($mouseOk -and $speedOk)
            threshold_1 = if ($mouseOk) { $mouse[0] } else { $null }
            threshold_2 = if ($mouseOk) { $mouse[1] } else { $null }
            acceleration = if ($mouseOk) { $mouse[2] } else { $null }
            speed = if ($speedOk) { $speed[0] } else { $null }
        }
    }
    bluetooth = [ordered]@{
        adapter_present = [bool]($bluetoothDriver -or $bluetoothPnp)
        adapter_name = if ($bluetoothDriver) { $bluetoothDriver.DeviceName } elseif ($bluetoothPnp) { $bluetoothPnp.FriendlyName } else { $null }
        driver_version = if ($bluetoothDriver) { $bluetoothDriver.DriverVersion } else { $null }
        pnp_status = if ($bluetoothPnp) { $bluetoothPnp.Status.ToString() } else { $null }
        pnp_problem_code = $bluetoothProblemCode
        radio_state = $radioState
        peripheral_role_supported = $peripheralRole
        hid_over_bluetooth_driver_present = Test-Path (Join-Path $env:SystemRoot 'System32\drivers\hidbth.sys')
        present_mouse_device_count = $mouseDevices.Count
        mouse_device_error_count = @($mouseDevices | Where-Object { $_.Status -ne 'OK' }).Count
        services = @($bluetoothServices)
    }
    network = [ordered]@{
        profiles = $profiles
        firewall_profiles = $firewall
        mini_pc_tcp_probe = [ordered]@{
            requested = [bool]$MiniPcHost
            port = if ($MiniPcHost) { $MiniPcPort } else { $null }
            reachable = if ($MiniPcHost) { [bool]$tcpProbe } else { $null }
        }
        note = 'No address, adapter identifier, rule or setting was collected or changed.'
    }
    not_executed = @(
        'software installation',
        'firewall change',
        'Bluetooth configuration change',
        'pairing',
        'mouse input injection',
        'service or scheduled task creation'
    )
}

$result | ConvertTo-Json -Depth 8
