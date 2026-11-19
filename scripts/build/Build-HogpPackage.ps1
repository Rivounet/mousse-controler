[CmdletBinding()]
param([string]$CertificateThumbprint)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$msbuild = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe'
$makeAppx = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe'
$signTool = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe'
$stage = Join-Path $root 'out\HogpPackage\stage'
$package = Join-Path $root 'out\HogpPackage\MousseControler.Hogp.msix'
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'Assets') | Out-Null

& $msbuild (Join-Path $root 'src\hogp\MousseHogp.vcxproj') /t:Rebuild /p:Configuration=Release /p:Platform=x64 /nologo /v:minimal
if ($LASTEXITCODE -ne 0) { throw 'HOGP engine build failed' }
& $msbuild (Join-Path $root 'src\hogp-launcher\MousseHogpLauncher.vcxproj') /t:Rebuild /p:Configuration=Release /p:Platform=x64 /nologo /v:minimal
if ($LASTEXITCODE -ne 0) { throw 'HOGP launcher build failed' }

if ($CertificateThumbprint) {
    foreach ($binary in @(
        (Join-Path $root 'src\hogp\out\Release\mousse-hogp.exe'),
        (Join-Path $root 'src\hogp-launcher\out\Release\mousse-hogp.exe')
    )) {
        & $signTool sign /sha1 $CertificateThumbprint /s My /fd SHA256 $binary
        if ($LASTEXITCODE -ne 0) { throw "Authenticode signing failed: $binary" }
    }
}

Copy-Item (Join-Path $root 'src\hogp\out\Release\mousse-hogp.exe') (Join-Path $stage 'mousse-hogp-packaged.exe') -Force
Copy-Item (Join-Path $root 'packaging\hogp\AppxManifest.xml') (Join-Path $stage 'AppxManifest.xml') -Force
Copy-Item (Join-Path $root 'src\hogp-launcher\out\Release\mousse-hogp.exe') (Join-Path $root 'out\Release\mousse-hogp.exe') -Force

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
& $makeAppx pack /d $stage /p $package /o
if ($LASTEXITCODE -ne 0) { throw 'MSIX packaging failed' }
if ($CertificateThumbprint) {
    & $signTool sign /sha1 $CertificateThumbprint /s My /fd SHA256 $package
    if ($LASTEXITCODE -ne 0) { throw 'MSIX signing failed' }
}
Get-FileHash -Algorithm SHA256 -LiteralPath $package | Select-Object Algorithm, Hash, Path
