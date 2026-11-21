[CmdletBinding()]
param([string]$CertificateThumbprint)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
. (Join-Path $PSScriptRoot 'Resolve-BuildTools.ps1')
$tools = Resolve-MousseBuildTools -RequirePackagingTools
$stage = Join-Path $root 'out\HogpPackage\stage'
$package = Join-Path $root 'out\HogpPackage\MousseControler.Hogp.msix'
$outRoot = [IO.Path]::GetFullPath((Join-Path $root 'out')) + [IO.Path]::DirectorySeparatorChar
$stage = [IO.Path]::GetFullPath($stage)
if (-not $stage.StartsWith($outRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clear package stage outside the repository output directory: $stage"
}
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'Assets') | Out-Null

$powerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$powerShellSignature = Get-AuthenticodeSignature -LiteralPath $powerShell
if ($powerShellSignature.Status -ne [Management.Automation.SignatureStatus]::Valid -or
    $powerShellSignature.SignerCertificate.Subject -notmatch '^CN=Microsoft Windows,') {
    throw 'The package host must be the valid Microsoft-signed Windows PowerShell binary.'
}

Copy-Item -LiteralPath $powerShell -Destination (Join-Path $stage 'powershell.exe') -Force
Copy-Item (Join-Path $root 'src\hogp-powershell\hogp.ps1') (Join-Path $stage 'hogp.ps1') -Force
Copy-Item (Join-Path $root 'packaging\hogp\AppxManifest.xml') (Join-Path $stage 'AppxManifest.xml') -Force

Add-Type -AssemblyName System.Drawing
foreach ($asset in @(
    @{ Name = 'StoreLogo.png'; Size = 50 },
    @{ Name = 'Square44x44Logo.png'; Size = 44 },
    @{ Name = 'Square150x150Logo.png'; Size = 150 }
)) {
    $bitmap = New-Object Drawing.Bitmap $asset.Size, $asset.Size
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([Drawing.Color]::FromArgb(45, 80, 120))
    $bitmap.Save((Join-Path $stage ('Assets\' + $asset.Name)), [Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose()
}
& $tools.MakeAppx pack /d $stage /p $package /o
if ($LASTEXITCODE -ne 0) { throw 'MSIX packaging failed' }
if ($CertificateThumbprint) {
    & $tools.SignTool sign /sha1 $CertificateThumbprint /s My /fd SHA256 $package
    if ($LASTEXITCODE -ne 0) { throw 'MSIX signing failed' }
}
Get-FileHash -Algorithm SHA256 -LiteralPath $package | Select-Object Algorithm, Hash, Path
