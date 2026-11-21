[CmdletBinding()]
param([string]$Root)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')) }
$Root = [IO.Path]::GetFullPath($Root)
$files = @(
    Get-ChildItem -LiteralPath (Join-Path $Root 'scripts') -Filter '*.ps1' -File -Recurse
    Get-ChildItem -LiteralPath (Join-Path $Root 'src') -Filter '*.ps1' -File -Recurse
) | Sort-Object FullName -Unique

$failures = New-Object System.Collections.Generic.List[object]
foreach ($file in $files) {
    $tokens = $null
    $errors = $null
    $null = [Management.Automation.Language.Parser]::ParseFile(
        $file.FullName, [ref]$tokens, [ref]$errors)
    foreach ($parseError in $errors) {
        $failures.Add([PSCustomObject]@{
            File = $file.FullName.Substring($Root.Length).TrimStart('\')
            Line = $parseError.Extent.StartLineNumber
            Message = $parseError.Message
        })
    }
}

if ($failures.Count -gt 0) {
    $failures | Format-Table -AutoSize | Out-String | Write-Error
    exit 1
}
Write-Output "PowerShell syntax valid: $($files.Count) active scripts parsed; none executed."
