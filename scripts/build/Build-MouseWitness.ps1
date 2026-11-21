[CmdletBinding()]
param([string]$OutputDirectory)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\MouseWitness' }
. (Join-Path $PSScriptRoot 'Resolve-BuildTools.ps1')
$tools = Resolve-MousseBuildTools
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'MouseWitness.exe'
& $tools.Compiler /nologo /target:winexe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /out:$executable /reference:System.dll /reference:System.Core.dll `
    /reference:System.Drawing.dll /reference:System.Windows.Forms.dll `
    (Join-Path $root 'scripts\qualification\MouseWitness.cs')
if ($LASTEXITCODE -ne 0) { throw "MouseWitness compilation failed: $LASTEXITCODE" }
Get-FileHash -Algorithm SHA256 -LiteralPath $executable | Select-Object Algorithm,Hash,Path
