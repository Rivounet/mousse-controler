[CmdletBinding()]
param([string]$OutputDirectory)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\PairingTool' }
. (Join-Path $PSScriptRoot 'Resolve-BuildTools.ps1')
$tools = Resolve-MousseBuildTools -RequireWindowsSdk
$source = Join-Path $root 'src\pairing-tool\PairingTool.cs'
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'PairingTool.exe'
& $tools.Compiler /nologo /target:exe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /out:$executable /reference:System.dll /reference:System.Core.dll `
    /reference:System.Web.Extensions.dll "/reference:$($tools.Runtime)" `
    "/reference:$($tools.InteropRuntime)" "/reference:$($tools.SystemRuntime)" `
    "/reference:$($tools.WindowsMetadata)" "/reference:$($tools.UniversalContract)" `
    "/reference:$($tools.FoundationContract)" $source
if ($LASTEXITCODE -ne 0) { throw "PairingTool compilation failed: $LASTEXITCODE" }
Get-FileHash -Algorithm SHA256 -LiteralPath $executable | Select-Object Algorithm, Hash, Path
