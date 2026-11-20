[CmdletBinding()]
param([string]$OutputDirectory)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\MouseWitness' }
$compiler = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) { throw 'Roslyn x64 compiler not found' }
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'MouseWitness.exe'
& $compiler /nologo /target:winexe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /out:$executable /reference:System.dll /reference:System.Core.dll `
    /reference:System.Drawing.dll /reference:System.Windows.Forms.dll `
    (Join-Path $root 'scripts\qualification\MouseWitness.cs')
if ($LASTEXITCODE -ne 0) { throw "MouseWitness compilation failed: $LASTEXITCODE" }
Get-FileHash -Algorithm SHA256 -LiteralPath $executable | Select-Object Algorithm,Hash,Path
