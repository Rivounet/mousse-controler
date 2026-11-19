[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Read-only inventory for the future position-feedback agent. The result omits
# user names, host names, addresses, adapter identifiers and firewall rules.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class MouseControlAuditNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool GetCursorPos(out POINT point);

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
}
'@

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
    [ordered]@{
        primary = $_.Primary
        bounds = [ordered]@{
            left = $_.Bounds.Left
            top = $_.Bounds.Top
            width = $_.Bounds.Width
            height = $_.Bounds.Height
        }
    }
})

$osCim = Invoke-Optional { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop }
$currentVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'

$result = [ordered]@{
    schema = 1
    diagnostic_mode = 'read-only'
    intended_machine_role = 'Windows HID target and position-feedback agent'
    os = [ordered]@{
        caption = if ($osCim) { $osCim.Caption } else { $currentVersion.ProductName }
        version = [Environment]::OSVersion.Version.ToString()
        architecture = if ($osCim) { $osCim.OSArchitecture } elseif ([Environment]::Is64BitOperatingSystem) { '64-bit' } else { '32-bit' }
        process_is_64_bit = [Environment]::Is64BitProcess
    }
    runtime = [ordered]@{
        powershell = $PSVersionTable.PSVersion.ToString()
        dotnet_cli = Get-CommandVersion -Name 'dotnet'
        dotnet_framework_full = [ordered]@{
            version = $dotNetVersion
            release = $dotNetRelease
        }
        inbox_csharp_compiler = [ordered]@{
            available = [bool]$csc
            framework = if ($csc) { if ($csc -like '*Framework64*') { 'Framework64' } else { 'Framework' } } else { $null }
        }
    }
    session = [ordered]@{
        process_session_id = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
        active_console_session_id = [MouseControlAuditNative]::WTSGetActiveConsoleSessionId()
        interactive = [Environment]::UserInteractive
    }
    cursor = [ordered]@{
        get_cursor_pos_succeeded = $cursorOk
        position = if ($cursorOk) { [ordered]@{ x = $cursor.X; y = $cursor.Y } } else { $null }
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
        adapter_present = [bool]$bluetoothDriver
        adapter_name = if ($bluetoothDriver) { $bluetoothDriver.DeviceName } else { $null }
        driver_version = if ($bluetoothDriver) { $bluetoothDriver.DriverVersion } else { $null }
        hid_over_bluetooth_driver_present = Test-Path (Join-Path $env:SystemRoot 'System32\drivers\hidbth.sys')
    }
    network = [ordered]@{
        profiles = $profiles
        firewall_profiles = $firewall
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
