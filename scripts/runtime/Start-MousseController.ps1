[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [string]$PythonPath = 'python.exe',
    [ValidateRange(1, 20)][int]$MaximumAttempts = 5,
    [ValidateRange(1, 300)][int]$RetryDelaySeconds = 30,
    [switch]$AllowMutableSource
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$config = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "Controller config not found: $config"
}
$manifest = Join-Path $root '.mousse-release.json'
$verifier = Join-Path $PSScriptRoot 'controller_release.py'
if (Test-Path -LiteralPath $manifest -PathType Leaf) {
    & $PythonPath -B $verifier verify --release $root | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Controller release integrity verification failed'
    }
}
elseif (-not $AllowMutableSource) {
    throw 'Mutable source launch refused; prepare an immutable controller release'
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
