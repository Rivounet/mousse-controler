[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [string]$PythonPath = 'python.exe',
    [ValidateRange(1, 20)][int]$MaximumAttempts = 5,
    [ValidateRange(1, 300)][int]$RetryDelaySeconds = 30
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$config = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "Controller config not found: $config"
}
$env:PYTHONPATH = Join-Path $root 'src'
for ($attempt = 1; $attempt -le $MaximumAttempts; $attempt++) {
    & $PythonPath -m mousse_controler.app serve --config $config
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) { exit 0 }
    if ($attempt -eq $MaximumAttempts) { exit $exitCode }
    Write-Warning "Controller exited with code $exitCode; retrying in $RetryDelaySeconds seconds (attempt $($attempt + 1)/$MaximumAttempts)."
    Start-Sleep -Seconds $RetryDelaySeconds
}
