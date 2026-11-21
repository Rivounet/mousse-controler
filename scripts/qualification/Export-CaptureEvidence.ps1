[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourcePath,
    [Parameter(Mandatory)][string]$DestinationPath,
    [Parameter(Mandatory)][int]$X,
    [Parameter(Mandatory)][int]$Y,
    [Parameter(Mandatory)][int]$Width,
    [Parameter(Mandatory)][int]$Height
)

$ErrorActionPreference = 'Stop'

function Get-Sha256Hex {
    param([Parameter(Mandatory)][string]$LiteralPath)

    $stream = [IO.File]::OpenRead($LiteralPath)
    try {
        $algorithm = [Security.Cryptography.SHA256]::Create()
        try {
            $hash = $algorithm.ComputeHash($stream)
            return ([BitConverter]::ToString($hash)).Replace('-', '')
        }
        finally {
            $algorithm.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

$source = [IO.Path]::GetFullPath($SourcePath)
$destination = [IO.Path]::GetFullPath($DestinationPath)
if ([IO.Path]::GetExtension($source) -ine '.png' -or
    [IO.Path]::GetExtension($destination) -ine '.png') {
    throw 'Capture evidence source and destination must be PNG files'
}
if ($Width -lt 1 -or $Height -lt 1 -or $X -lt 0 -or $Y -lt 0) {
    throw 'Invalid capture evidence crop rectangle'
}

Add-Type -AssemblyName System.Drawing
$image = [Drawing.Bitmap]::FromFile($source)
try {
    if ($X + $Width -gt $image.Width -or $Y + $Height -gt $image.Height) {
        throw 'Capture evidence crop exceeds source image bounds'
    }
    $rectangle = [Drawing.Rectangle]::new($X, $Y, $Width, $Height)
    $cropped = $image.Clone($rectangle, $image.PixelFormat)
    try {
        $parent = [IO.Path]::GetDirectoryName($destination)
        [IO.Directory]::CreateDirectory($parent) | Out-Null
        $temporary = "$destination.tmp.png"
        $cropped.Save($temporary, [Drawing.Imaging.ImageFormat]::Png)
        Move-Item -LiteralPath $temporary -Destination $destination -Force
    }
    finally {
        $cropped.Dispose()
    }
}
finally {
    $image.Dispose()
}

[ordered]@{
    sha256 = Get-Sha256Hex -LiteralPath $destination
    width = $Width
    height = $Height
} | ConvertTo-Json -Compress
