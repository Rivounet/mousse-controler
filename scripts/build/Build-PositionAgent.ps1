[CmdletBinding()]
param(
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\PositionAgent' }
$source = Join-Path $root 'src\position-agent\PositionAgent.cs'
$manifest = Join-Path $root 'src\position-agent\PositionAgent.manifest'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework 4.8 x64 compiler not found' }

$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'PositionAgent.exe'
& $compiler /nologo /target:exe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /win32manifest:$manifest /out:$executable `
    /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll `
    /reference:System.Security.dll /reference:System.Web.Extensions.dll `
    $source
if ($LASTEXITCODE -ne 0) { throw "PositionAgent compilation failed: $LASTEXITCODE" }
Copy-Item -LiteralPath (Join-Path $root 'src\position-agent\agent.example.json') -Destination $output -Force
Get-FileHash -Algorithm SHA256 -LiteralPath $executable | Select-Object Algorithm, Hash, Path
