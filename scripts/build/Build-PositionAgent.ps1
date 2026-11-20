[CmdletBinding()]
param(
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\PositionAgent' }
$source = Join-Path $root 'src\position-agent\PositionAgent.cs'
$manifest = Join-Path $root 'src\position-agent\PositionAgent.manifest'
$compiler = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
$windowsMetadata = 'C:\Program Files (x86)\Windows Kits\10\UnionMetadata\10.0.26100.0\Facade\windows.winmd'
$universalContract = 'C:\Program Files (x86)\Windows Kits\10\References\10.0.26100.0\Windows.Foundation.UniversalApiContract\19.0.0.0\Windows.Foundation.UniversalApiContract.winmd'
$foundationContract = 'C:\Program Files (x86)\Windows Kits\10\References\10.0.26100.0\Windows.Foundation.FoundationContract\4.0.0.0\Windows.Foundation.FoundationContract.winmd'
$runtime = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\System.Runtime.WindowsRuntime.dll'
$interopRuntime = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\System.Runtime.InteropServices.WindowsRuntime.dll'
$systemRuntime = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\System.Runtime.dll'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Roslyn x64 compiler not found' }

$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'PositionAgent.exe'
& $compiler /nologo /target:exe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /win32manifest:$manifest /out:$executable `
    /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll `
    /reference:System.Security.dll /reference:System.Web.Extensions.dll `
    /reference:$runtime /reference:$interopRuntime /reference:$systemRuntime `
    /reference:$windowsMetadata /reference:$universalContract /reference:$foundationContract `
    $source
if ($LASTEXITCODE -ne 0) { throw "PositionAgent compilation failed: $LASTEXITCODE" }
Copy-Item -LiteralPath (Join-Path $root 'src\position-agent\agent.example.json') -Destination $output -Force
Get-FileHash -Algorithm SHA256 -LiteralPath $executable | Select-Object Algorithm, Hash, Path
