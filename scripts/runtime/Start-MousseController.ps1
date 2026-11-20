[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [string]$PythonPath = 'python.exe'
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$config = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "Controller config not found: $config"
}
$env:PYTHONPATH = Join-Path $root 'src'
& $PythonPath -m mousse_controler.app serve --config $config
exit $LASTEXITCODE
