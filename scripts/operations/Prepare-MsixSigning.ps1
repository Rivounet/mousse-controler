[CmdletBinding()]
param(
    [ValidateSet('Create', 'Status', 'Restore', 'Qualify')][string]$Action = 'Status',
    [string]$KeyDirectory = (Join-Path $env:LOCALAPPDATA 'MousseControler\Signing\msix-v2'),
    [string]$PackagePath,
    [string]$EvidencePath
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$subject = 'CN=MousseControler'
$metadataPath = Join-Path $KeyDirectory 'metadata.json'
$pfxPath = Join-Path $KeyDirectory 'signing-key.pfx'
$passwordPath = Join-Path $KeyDirectory 'password.dpapi'
$publicPath = Join-Path $KeyDirectory 'signing-public.cer'
if (-not $PackagePath) { $PackagePath = Join-Path $root 'out\HogpPackage\MousseControler.Hogp.msix' }
if (-not $EvidencePath) { $EvidencePath = Join-Path $root 'out\qualification\codex-environment\signing.json' }

function Get-KeyState {
    $metadata = if (Test-Path -LiteralPath $metadataPath -PathType Leaf) {
        Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
    } else { $null }
    $certificate = if ($metadata -and $metadata.thumbprint) {
        Get-Item -LiteralPath ("Cert:\CurrentUser\My\" + $metadata.thumbprint) -ErrorAction SilentlyContinue
    } else { $null }
    $aclRestricted = $false
    if (Test-Path -LiteralPath $KeyDirectory -PathType Container) {
        $currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $rules = @((Get-Acl -LiteralPath $KeyDirectory).Access)
        $unexpected = @($rules | Where-Object {
            -not $_.IsInherited -and $_.AccessControlType -eq 'Allow' -and
            $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin @($currentSid, 'S-1-5-18')
        })
        $inherited = @($rules | Where-Object { $_.IsInherited })
        $aclRestricted = $unexpected.Count -eq 0 -and $inherited.Count -eq 0 -and `
            @($rules | Where-Object { -not $_.IsInherited }).Count -eq 2
    }
    $ready = [bool](
        $metadata -and $certificate -and $certificate.HasPrivateKey -and
        (Test-Path -LiteralPath $pfxPath -PathType Leaf) -and
        (Test-Path -LiteralPath $passwordPath -PathType Leaf) -and
        (Test-Path -LiteralPath $publicPath -PathType Leaf) -and $aclRestricted
    )
    [ordered]@{
        ready = $ready
        metadata_present = [bool]$metadata
        certificate_present = [bool]$certificate
        private_key_present = [bool]($certificate -and $certificate.HasPrivateKey)
        encrypted_pfx_present = Test-Path -LiteralPath $pfxPath -PathType Leaf
        dpapi_secret_present = Test-Path -LiteralPath $passwordPath -PathType Leaf
        public_certificate_present = Test-Path -LiteralPath $publicPath -PathType Leaf
        acl_restricted = $aclRestricted
        thumbprint = if ($metadata) { $metadata.thumbprint } else { $null }
        subject = if ($metadata) { $metadata.subject } else { $null }
        not_after_utc = if ($metadata) { $metadata.not_after_utc } else { $null }
    }
}

function Protect-KeyDirectory {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $currentPrincipal = '*' + $identity.User.Value
    $systemPrincipal = '*S-1-5-18'
    & "$env:SystemRoot\System32\icacls.exe" $KeyDirectory '/inheritance:r' '/grant:r' `
        "${currentPrincipal}:(OI)(CI)F" "${systemPrincipal}:(OI)(CI)F" '/Q' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Key directory ACL restriction failed: $LASTEXITCODE" }
}

function Write-Result([object]$Result, [string]$Path) {
    $json = $Result | ConvertTo-Json -Depth 10
    if ($Path) {
        $fullPath = [IO.Path]::GetFullPath($Path)
        $outRoot = [IO.Path]::GetFullPath((Join-Path $root 'out')) + [IO.Path]::DirectorySeparatorChar
        if (-not $fullPath.StartsWith($outRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Signing evidence must remain below the repository out directory.'
        }
        New-Item -ItemType Directory -Force -Path (Split-Path $fullPath) | Out-Null
        Set-Content -LiteralPath $fullPath -Value ($json + [Environment]::NewLine) -Encoding UTF8
    }
    $json
}

try {
    if ($Action -eq 'Status') {
        $state = Get-KeyState
        [ordered]@{
            contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'
            action = 'Status'
            status = if ($state.ready) { 'READY' } else { 'BLOCKED' }
            key = $state
            trust_store_modified = $false
            package_installed = $false
        } | ConvertTo-Json -Depth 7
        if (-not $state.ready) { exit 2 }
        exit 0
    }

    if ($Action -eq 'Create') {
        $existing = Get-KeyState
        if ($existing.metadata_present) {
            [ordered]@{
                contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'
                action = 'Create'
                status = if ($existing.ready) { 'READY' } else { 'BLOCKED' }
                idempotent_reuse = $true
                key = $existing
                trust_store_modified = $false
            } | ConvertTo-Json -Depth 7
            if (-not $existing.ready) { exit 2 }
            exit 0
        }
        $createdCertificate = $null
        $createdDirectory = $false
        try {
            if (-not (Test-Path -LiteralPath $KeyDirectory -PathType Container)) {
                New-Item -ItemType Directory -Path $KeyDirectory -Force | Out-Null
                $createdDirectory = $true
            }
            Protect-KeyDirectory
            $passwordBytes = New-Object byte[] 36
            $random = [Security.Cryptography.RandomNumberGenerator]::Create()
            try { $random.GetBytes($passwordBytes) } finally { $random.Dispose() }
            $passwordPlain = [Convert]::ToBase64String($passwordBytes)
            $password = ConvertTo-SecureString -String $passwordPlain -AsPlainText -Force
            $passwordPlain = $null
            [Array]::Clear($passwordBytes, 0, $passwordBytes.Length)
            $createdCertificate = New-SelfSignedCertificate -Type Custom -Subject $subject `
                -CertStoreLocation 'Cert:\CurrentUser\My' -KeyAlgorithm RSA -KeyLength 3072 `
                -HashAlgorithm SHA256 -KeyExportPolicy Exportable -KeyUsage DigitalSignature `
                -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3') `
                -FriendlyName 'Mousse-controler MSIX signing v2' -NotAfter (Get-Date).AddYears(5)
            Export-PfxCertificate -Cert $createdCertificate -FilePath $pfxPath -Password $password -ChainOption EndEntityCertOnly -Force | Out-Null
            Export-Certificate -Cert $createdCertificate -FilePath $publicPath -Type CERT -Force | Out-Null
            $password | ConvertFrom-SecureString | Set-Content -LiteralPath $passwordPath -Encoding ASCII
            $metadata = [ordered]@{
                contract = 'MC-CODEX-ENVIRONMENT-001/signing-key-v1'
                subject = $createdCertificate.Subject
                thumbprint = $createdCertificate.Thumbprint
                created_at_utc = [datetime]::UtcNow.ToString('o')
                not_after_utc = $createdCertificate.NotAfter.ToUniversalTime().ToString('o')
                algorithm = $createdCertificate.PublicKey.Oid.FriendlyName
                key_size = [Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($createdCertificate).KeySize
                public_certificate_sha256 = (Get-FileHash -LiteralPath $publicPath -Algorithm SHA256).Hash
                encrypted_pfx_sha256 = (Get-FileHash -LiteralPath $pfxPath -Algorithm SHA256).Hash
                password_protection = 'Windows DPAPI CurrentUser'
            }
            $metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
            Protect-KeyDirectory
            $state = Get-KeyState
            if (-not $state.ready) { throw 'Created signing key failed its storage checks.' }
            [ordered]@{
                contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'
                action = 'Create'
                status = 'READY'
                idempotent_reuse = $false
                key = $state
                trust_store_modified = $false
                package_installed = $false
            } | ConvertTo-Json -Depth 7
            exit 0
        } catch {
            if ($createdCertificate) { Remove-Item -LiteralPath ("Cert:\CurrentUser\My\" + $createdCertificate.Thumbprint) -Force -ErrorAction SilentlyContinue }
            if ($createdDirectory -and (Test-Path -LiteralPath $KeyDirectory)) { Remove-Item -LiteralPath $KeyDirectory -Recurse -Force -ErrorAction SilentlyContinue }
            throw
        }
    }

    if ($Action -eq 'Restore') {
        if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf) -or
            -not (Test-Path -LiteralPath $pfxPath -PathType Leaf) -or
            -not (Test-Path -LiteralPath $passwordPath -PathType Leaf)) {
            throw 'Protected signing-key material is incomplete.'
        }
        $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
        $protectedPassword = (Get-Content -LiteralPath $passwordPath -Raw).Trim()
        $password = $protectedPassword | ConvertTo-SecureString
        $restored = Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation 'Cert:\CurrentUser\My' `
            -Password $password -Exportable
        $restoredCertificate = @($restored | Where-Object { $_.Thumbprint -eq $metadata.thumbprint }) | Select-Object -First 1
        if (-not $restoredCertificate -or -not $restoredCertificate.HasPrivateKey) {
            throw 'Protected PFX restoration did not recover the expected private key.'
        }
        $state = Get-KeyState
        if (-not $state.ready) { throw 'Restored signing key failed its storage checks.' }
        [ordered]@{
            contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'
            action = 'Restore'
            status = 'READY'
            key = $state
            trust_store_modified = $false
            package_installed = $false
        } | ConvertTo-Json -Depth 7
        exit 0
    }

    $state = Get-KeyState
    if (-not $state.ready) { throw 'Signing key is not ready; run Create first.' }
    $certificate = Get-Item -LiteralPath ("Cert:\CurrentUser\My\" + $state.thumbprint)
    $buildOutput = @(& (Join-Path $root 'scripts\build\Build-HogpPackage.ps1') -CertificateThumbprint $state.thumbprint 2>&1)
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PackagePath -PathType Leaf)) {
        throw ('MSIX build or signing failed: ' + ($buildOutput -join ' '))
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $PackagePath
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($PackagePath)
    try {
        $entry = $archive.GetEntry('AppxManifest.xml')
        if (-not $entry) { throw 'Signed package has no AppxManifest.xml.' }
        $reader = New-Object IO.StreamReader($entry.Open())
        try { [xml]$manifest = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $archive.Dispose() }
    $identity = $manifest.Package.Identity
    $signerMatches = [bool]($signature.SignerCertificate -and $signature.SignerCertificate.Thumbprint -eq $state.thumbprint)
    $identityMatches = $identity.Publisher -eq $subject -and $identity.Name -eq 'Rivounet.MousseControler.Hogp'
    $versionAdvancesInstalled = [version]$identity.Version -gt [version]'1.0.0.2'
    $trusted = @(
        "Cert:\CurrentUser\TrustedPeople\$($state.thumbprint)",
        "Cert:\LocalMachine\TrustedPeople\$($state.thumbprint)",
        "Cert:\CurrentUser\Root\$($state.thumbprint)",
        "Cert:\LocalMachine\Root\$($state.thumbprint)"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $passed = $signerMatches -and $identityMatches -and $versionAdvancesInstalled
    $result = [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'
        action = 'Qualify'
        status = if ($passed) { 'PASS' } else { 'FAIL' }
        key = $state
        package = [ordered]@{
            sha256 = (Get-FileHash -LiteralPath $PackagePath -Algorithm SHA256).Hash
            size = (Get-Item -LiteralPath $PackagePath).Length
            identity_name = $identity.Name
            publisher = $identity.Publisher
            version = $identity.Version
        }
        signature = [ordered]@{
            embedded = [bool]$signature.SignerCertificate
            signer_matches_key = $signerMatches
            authenticode_status = $signature.Status.ToString()
            authenticode_message = $signature.StatusMessage
        }
        compatibility = [ordered]@{
            identity_matches_manifest = $identityMatches
            version_advances_installed_1_0_0_2 = $versionAdvancesInstalled
            windows_update_requires_same_trusted_publisher = $true
        }
        transition = [ordered]@{
            new_certificate_trusted = [bool]$trusted
            trust_install_required_before_update = -not [bool]$trusted
            existing_msix_replaced = $false
            rollback = 'Keep version 1.0.0.2 and its trusted public certificate until the new certificate is authorized and the update succeeds.'
        }
        trust_store_modified = $false
        package_installed = $false
    }
    Write-Result $result $EvidencePath
    if (-not $passed) { exit 1 }
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch [UnauthorizedAccessException] {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'; action = $Action; status = 'BLOCKED'; boundary = 'windows-user-certificate-or-key-storage'; error = $_.Exception.Message } | ConvertTo-Json
    exit 2
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/prepare-msix-signing-v1'; action = $Action; status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json
    exit 1
}
