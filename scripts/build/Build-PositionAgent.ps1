[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [string]$QualificationManifestPath
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\PositionAgent' }
$source = Join-Path $root 'src\position-agent\PositionAgent.cs'
$manifest = Join-Path $root 'src\position-agent\PositionAgent.manifest'
. (Join-Path $PSScriptRoot 'Resolve-BuildTools.ps1')
$tools = Resolve-MousseBuildTools -RequireWindowsSdk

$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$executable = Join-Path $output 'PositionAgent.exe'
& $tools.Compiler /nologo /target:exe /optimize+ /platform:x64 /warn:4 /warnaserror+ `
    /win32manifest:$manifest /out:$executable `
    /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll `
    /reference:System.Security.dll /reference:System.Web.Extensions.dll `
    "/reference:$($tools.Runtime)" "/reference:$($tools.InteropRuntime)" `
    "/reference:$($tools.SystemRuntime)" "/reference:$($tools.WindowsMetadata)" `
    "/reference:$($tools.UniversalContract)" "/reference:$($tools.FoundationContract)" `
    $source
if ($LASTEXITCODE -ne 0) { throw "PositionAgent compilation failed: $LASTEXITCODE" }
Copy-Item -LiteralPath (Join-Path $root 'src\position-agent\agent.example.json') -Destination $output -Force
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $executable
if ($QualificationManifestPath) {
    $qualificationManifest = [IO.Path]::GetFullPath($QualificationManifestPath)
    $manifestParent = Split-Path -Parent $qualificationManifest
    if ($manifestParent) { New-Item -ItemType Directory -Force -Path $manifestParent | Out-Null }
    [PSCustomObject]@{
        contract = 'MC-ROBUSTNESS-R4-001'
        target_framework = '.NET Framework 4.x (v4.0.30319 reference assemblies)'
        compiler_version = $tools.CompilerVersion
        windows_sdk_version = $tools.WindowsSdkVersion
        options = @('/target:exe', '/optimize+', '/platform:x64', '/warn:4', '/warnaserror+')
        artifact = [PSCustomObject]@{
            path = $executable
            size = (Get-Item -LiteralPath $executable).Length
            sha256 = $hash.Hash.ToLowerInvariant()
        }
        installed = $false
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $qualificationManifest -Encoding UTF8
}
$hash | Select-Object Algorithm, Hash, Path
