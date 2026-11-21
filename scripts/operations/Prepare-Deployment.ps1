[CmdletBinding()]
param(
    [string]$QualificationSummary,
    [string]$PackagePath,
    [string]$SigningEvidence,
    [string]$ExpectedGitSha
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $QualificationSummary) { $QualificationSummary = Join-Path $root 'out\qualification\codex-environment\summary.json' }
if (-not $PackagePath) { $PackagePath = Join-Path $root 'out\HogpPackage\MousseControler.Hogp.msix' }
if (-not $SigningEvidence) { $SigningEvidence = Join-Path $root 'out\qualification\codex-environment\signing.json' }

try {
    $head = (& git -C $root rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Git HEAD is unavailable.' }
    $dirty = @(& git -C $root status --short)
    $qualification = if (Test-Path -LiteralPath $QualificationSummary -PathType Leaf) { Get-Content -LiteralPath $QualificationSummary -Raw | ConvertFrom-Json } else { $null }
    $signing = if ($SigningEvidence -and (Test-Path -LiteralPath $SigningEvidence -PathType Leaf)) { Get-Content -LiteralPath $SigningEvidence -Raw | ConvertFrom-Json } else { $null }
    $package = if (Test-Path -LiteralPath $PackagePath -PathType Leaf) {
        [ordered]@{ available = $true; sha256 = (Get-FileHash -LiteralPath $PackagePath -Algorithm SHA256).Hash; size = (Get-Item -LiteralPath $PackagePath).Length }
    } else { [ordered]@{ available = $false; sha256 = $null; size = $null } }
    $checks = [ordered]@{
        git_head_matches_expected = (-not $ExpectedGitSha) -or $head -eq $ExpectedGitSha
        git_clean = $dirty.Count -eq 0
        qualification_pass = [bool]($qualification -and $qualification.verdict -eq 'PASS' -and $qualification.git_sha -eq $head)
        package_available = $package.available
        signing_qualified = [bool](
            $signing -and $signing.status -eq 'PASS' -and
            $signing.signature.signer_matches_key -and
            $package.available -and
            $signing.package.sha256 -and
            $signing.package.sha256 -eq $package.sha256 -and
            $signing.package.identity_name -eq 'Rivounet.MousseControler.Hogp' -and
            $signing.package.publisher -eq 'CN=MousseControler' -and
            [version]$signing.package.version -ge [version]'1.0.0.3'
        )
        trust_install_authorized = $false
        package_install_authorized = $false
    }
    $prepared = $checks.git_head_matches_expected -and $checks.git_clean -and $checks.qualification_pass -and $checks.package_available -and $checks.signing_qualified
    [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/prepare-deployment-v1'
        status = if ($prepared) { 'PREPARED_NOT_AUTHORIZED' } else { 'PARTIAL' }
        git_sha = $head
        checks = $checks
        package = $package
        effects = 'read-only'
        next_authorization = if ($prepared) { 'Install the new public certificate, then replace the MSIX under a separate operational mandate.' } else { 'Complete failed preconditions before requesting deployment authorization.' }
    } | ConvertTo-Json -Depth 7
    if (-not $prepared) { exit 2 }
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/prepare-deployment-v1'; status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json
    exit 1
}
