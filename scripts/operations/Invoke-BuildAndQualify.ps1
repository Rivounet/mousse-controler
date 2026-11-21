[CmdletBinding()]
param(
    [ValidateSet('software', 'build', 'full-local')][string]$Profile = 'full-local',
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'out\qualification\codex-environment' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$outRoot = [IO.Path]::GetFullPath((Join-Path $root 'out')) + [IO.Path]::DirectorySeparatorChar
if (-not $OutputDirectory.StartsWith($outRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Qualification output must remain below the repository out directory.'
}

try {
    & python -B (Join-Path $root 'scripts\qualification\qualify.py') --profile $Profile --output-dir $OutputDirectory
    $qualificationExit = $LASTEXITCODE
    $summaryPath = Join-Path $OutputDirectory 'summary.json'
    $summary = if (Test-Path -LiteralPath $summaryPath) { Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json } else { $null }
    [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/build-and-qualify-v1'
        status = if ($qualificationExit -eq 0) { 'PASS' } elseif ($qualificationExit -eq 2) { 'BLOCKED' } else { 'FAIL' }
        profile = $Profile
        git_sha = if ($summary) { $summary.git_sha } else { $null }
        test_verdict = if ($summary) { $summary.verdict } else { $null }
        duration_seconds = if ($summary) { $summary.duration_seconds } else { $null }
        summary_path = $summaryPath
        material_operations = $false
    } | ConvertTo-Json -Depth 5
    exit $qualificationExit
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/build-and-qualify-v1'; status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json
    exit 1
}
