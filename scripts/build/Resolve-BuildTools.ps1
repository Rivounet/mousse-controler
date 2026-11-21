Set-StrictMode -Version 2.0

function Get-HighestVersionDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][scriptblock]$Accept
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $null }
    $candidates = foreach ($directory in Get-ChildItem -LiteralPath $Root -Directory -ErrorAction Stop) {
        $parsed = $null
        if ([version]::TryParse($directory.Name, [ref]$parsed) -and (& $Accept $directory.FullName)) {
            [PSCustomObject]@{ Version = $parsed; Path = $directory.FullName }
        }
    }
    return $candidates | Sort-Object Version -Descending | Select-Object -First 1
}
function Resolve-MousseBuildTools {
    [CmdletBinding()]
    param(
        [switch]$RequireWindowsSdk,
        [switch]$RequirePackagingTools
    )

    if ($RequirePackagingTools) { $RequireWindowsSdk = $true }

    $programFilesX86 = [Environment]::GetFolderPath('ProgramFilesX86')
    if (-not $programFilesX86) { throw 'Program Files (x86) cannot be located.' }

    $visualStudioRoots = New-Object System.Collections.Generic.List[string]
    if ($env:VSINSTALLDIR) { $visualStudioRoots.Add($env:VSINSTALLDIR) }
    $vswhere = Join-Path $programFilesX86 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $vswhere -PathType Leaf) {
        $discovered = & $vswhere -products '*' -requires Microsoft.Component.MSBuild `
            -property installationPath -format value
        if ($LASTEXITCODE -ne 0) { throw "Visual Studio discovery failed: $LASTEXITCODE" }
        foreach ($path in $discovered) {
            if ($path) { $visualStudioRoots.Add([string]$path) }
        }
    }

    $compilerCandidates = foreach ($root in $visualStudioRoots | Select-Object -Unique) {
        Join-Path $root 'MSBuild\Current\Bin\Roslyn\csc.exe'
        Join-Path $root 'MSBuild\15.0\Bin\Roslyn\csc.exe'
    }
    $compiler = $compilerCandidates | Where-Object {
        Test-Path -LiteralPath $_ -PathType Leaf
    } | Select-Object -First 1
    if (-not $compiler) {
        throw 'Compatible Roslyn compiler not found through VSINSTALLDIR or vswhere.'
    }

    $result = [ordered]@{
        Compiler = [IO.Path]::GetFullPath($compiler)
        CompilerVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($compiler).ProductVersion
        VisualStudioRoot = [IO.Path]::GetFullPath(
            (Split-Path (Split-Path (Split-Path (Split-Path (Split-Path $compiler))))))
    }
    if (-not $RequireWindowsSdk) { return [PSCustomObject]$result }

    $kitsRoot = $null
    try {
        $kitsRoot = (Get-ItemProperty `
            'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots' `
            -Name KitsRoot10 -ErrorAction Stop).KitsRoot10
    } catch {
        $kitsRoot = Join-Path $programFilesX86 'Windows Kits\10'
    }
    if (-not (Test-Path -LiteralPath $kitsRoot -PathType Container)) {
        throw 'Windows 10/11 SDK root was not found.'
    }

    $metadataRoot = Join-Path $kitsRoot 'UnionMetadata'
    $metadata = Get-HighestVersionDirectory -Root $metadataRoot -Accept {
        param($candidate)
        Test-Path -LiteralPath (Join-Path $candidate 'Facade\windows.winmd') -PathType Leaf
    }
    if (-not $metadata) { throw 'No compatible Windows SDK metadata was found.' }

    $sdkVersion = $metadata.Version.ToString()
    $referenceRoot = Join-Path (Join-Path $kitsRoot 'References') $sdkVersion
    $universalRoot = Join-Path $referenceRoot 'Windows.Foundation.UniversalApiContract'
    $foundationRoot = Join-Path $referenceRoot 'Windows.Foundation.FoundationContract'
    $universal = Get-HighestVersionDirectory -Root $universalRoot -Accept {
        param($candidate)
        Test-Path -LiteralPath `
            (Join-Path $candidate 'Windows.Foundation.UniversalApiContract.winmd') -PathType Leaf
    }
    $foundation = Get-HighestVersionDirectory -Root $foundationRoot -Accept {
        param($candidate)
        Test-Path -LiteralPath `
            (Join-Path $candidate 'Windows.Foundation.FoundationContract.winmd') -PathType Leaf
    }
    if (-not $universal -or -not $foundation) {
        throw "Required Windows Runtime contracts are missing from SDK $sdkVersion."
    }

    $frameworkCandidates = @(
        (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'),
        (Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319')
    )
    $framework = $frameworkCandidates | Where-Object {
        Test-Path -LiteralPath (Join-Path $_ 'System.Runtime.WindowsRuntime.dll') -PathType Leaf
    } | Select-Object -First 1
    if (-not $framework) { throw '.NET Framework 4.x Windows Runtime references were not found.' }

    $result.WindowsSdkRoot = [IO.Path]::GetFullPath($kitsRoot)
    $result.WindowsSdkVersion = $sdkVersion
    $result.WindowsMetadata = Join-Path $metadata.Path 'Facade\windows.winmd'
    $result.UniversalContract = Join-Path $universal.Path 'Windows.Foundation.UniversalApiContract.winmd'
    $result.FoundationContract = Join-Path $foundation.Path 'Windows.Foundation.FoundationContract.winmd'
    $result.FrameworkRoot = [IO.Path]::GetFullPath($framework)
    $result.Runtime = Join-Path $framework 'System.Runtime.WindowsRuntime.dll'
    $result.InteropRuntime = Join-Path $framework 'System.Runtime.InteropServices.WindowsRuntime.dll'
    $result.SystemRuntime = Join-Path $framework 'System.Runtime.dll'
    if ($RequirePackagingTools) {
        $sdkBin = Join-Path (Join-Path (Join-Path $kitsRoot 'bin') $sdkVersion) 'x64'
        $makeAppx = Join-Path $sdkBin 'makeappx.exe'
        $signTool = Join-Path $sdkBin 'signtool.exe'
        if (-not (Test-Path -LiteralPath $makeAppx -PathType Leaf) -or
            -not (Test-Path -LiteralPath $signTool -PathType Leaf)) {
            throw "Windows SDK packaging tools are missing from SDK $sdkVersion."
        }
        $result.MakeAppx = $makeAppx
        $result.SignTool = $signTool
    }
    return [PSCustomObject]$result
}
