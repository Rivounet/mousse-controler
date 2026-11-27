[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Acquire', 'Renew', 'Status', 'Release')]
    [string]$Action,
    [Parameter(Mandatory)][string]$LeasePath,
    [string]$RunId,
    [ValidateSet('Backend', 'Target')][string]$Role,
    [string]$PeerHost,
    [string]$GitSha,
    [string]$OwnerToken,
    [ValidateRange(60, 3600)][int]$TtlSeconds = 300
)

$ErrorActionPreference = 'Stop'

function Get-Sha256Hex([string]$Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '')
    }
    finally {
        $sha256.Dispose()
        [Array]::Clear($bytes, 0, $bytes.Length)
    }
}

function New-OwnerToken {
    $bytes = New-Object byte[] 32
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
        return ([BitConverter]::ToString($bytes)).Replace('-', '')
    }
    finally {
        $random.Dispose()
        [Array]::Clear($bytes, 0, $bytes.Length)
    }
}

function Test-FixedHexEqual([string]$Left, [string]$Right) {
    if ($null -eq $Left -or $null -eq $Right -or $Left.Length -ne $Right.Length) {
        return $false
    }
    $difference = 0
    for ($index = 0; $index -lt $Left.Length; $index++) {
        $difference = $difference -bor ([int]$Left[$index] -bxor [int]$Right[$index])
    }
    return $difference -eq 0
}

function ConvertTo-UtcInstant([string]$Value) {
    try {
        $instant = [DateTimeOffset]::Parse(
            $Value, [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind)
    }
    catch {
        throw 'Qualification lease contains an invalid UTC instant'
    }
    return $instant.ToUniversalTime()
}

function Read-Lease([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        $state = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    }
    catch {
        throw 'Qualification lease is not valid JSON'
    }
    if ($state.schema -ne 'mousse-qualification-lease-v1' -or
            $state.run_id -notmatch '^[0-9a-f-]{36}$' -or
            $state.role -notin @('backend', 'target') -or
            $state.git_sha -notmatch '^[0-9a-f]{40}([0-9a-f]{24})?$' -or
            $state.owner_token_sha256 -notmatch '^[0-9A-F]{64}$') {
        throw 'Qualification lease schema is invalid'
    }
    $null = ConvertTo-UtcInstant $state.expires_at_utc
    return $state
}

function Write-Lease([string]$Path, [System.Collections.IDictionary]$State) {
    $temporary = "$Path.$([Guid]::NewGuid().ToString('N')).tmp"
    $encoding = New-Object Text.UTF8Encoding($false)
    try {
        [IO.File]::WriteAllText(
            $temporary, ($State | ConvertTo-Json -Compress), $encoding)
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function ConvertTo-PublicStatus($State) {
    if ($null -eq $State) {
        return [ordered]@{ present = $false; active = $false }
    }
    $expires = ConvertTo-UtcInstant $State.expires_at_utc
    return [ordered]@{
        present = $true
        active = $expires -gt [DateTimeOffset]::UtcNow
        observed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        schema = $State.schema
        run_id = $State.run_id
        role = $State.role
        machine = $State.machine
        peer_host = $State.peer_host
        git_sha = $State.git_sha
        acquired_at_utc = $State.acquired_at_utc
        renewed_at_utc = $State.renewed_at_utc
        expires_at_utc = $State.expires_at_utc
    }
}

function Assert-RunId([string]$Value) {
    $parsed = [Guid]::Empty
    if (-not [Guid]::TryParseExact($Value, 'D', [ref]$parsed)) {
        throw '-RunId must be a canonical GUID'
    }
    return $parsed.ToString('D')
}

$lease = [IO.Path]::GetFullPath($LeasePath)
$parent = [IO.Path]::GetDirectoryName($lease)
if ($Action -eq 'Acquire') {
    [IO.Directory]::CreateDirectory($parent) | Out-Null
}
elseif (-not [IO.Directory]::Exists($parent)) {
    throw 'Qualification lease directory does not exist'
}

$lockPath = "$lease.lock"
$lock = $null
$deadline = [DateTimeOffset]::UtcNow.AddSeconds(5)
do {
    try {
        $lock = [IO.File]::Open(
            $lockPath, [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    }
    catch [IO.IOException] {
        if ([DateTimeOffset]::UtcNow -ge $deadline) {
            throw 'Qualification lease lock deadline exceeded'
        }
        Start-Sleep -Milliseconds 50
    }
} while ($null -eq $lock)

try {
    $state = Read-Lease $lease
    if ($Action -eq 'Status') {
        ConvertTo-PublicStatus $state | ConvertTo-Json -Compress
        return
    }

    $normalizedRunId = Assert-RunId $RunId
    if ($OwnerToken -and $OwnerToken -notmatch '^[0-9A-Fa-f]{64}$') {
        throw '-OwnerToken must contain 64 hexadecimal characters'
    }

    if ($Action -eq 'Acquire') {
        if (-not $Role -or [string]::IsNullOrWhiteSpace($PeerHost) -or
                $GitSha -notmatch '^[0-9A-Fa-f]{40}([0-9A-Fa-f]{24})?$') {
            throw 'Acquire requires -Role, -PeerHost and a 40- or 64-hex -GitSha'
        }
        $expiredRunId = $null
        if ($null -ne $state) {
            $expires = ConvertTo-UtcInstant $state.expires_at_utc
            if ($expires -gt [DateTimeOffset]::UtcNow) {
                throw "Qualification host is already leased by run $($state.run_id)"
            }
            $expiredRunId = $state.run_id
        }
        $token = if ($OwnerToken) { $OwnerToken.ToUpperInvariant() } else { New-OwnerToken }
        $now = [DateTimeOffset]::UtcNow
        $newState = [ordered]@{
            schema = 'mousse-qualification-lease-v1'
            run_id = $normalizedRunId
            role = $Role.ToLowerInvariant()
            machine = [Environment]::MachineName.ToUpperInvariant()
            peer_host = $PeerHost.Trim().ToUpperInvariant()
            git_sha = $GitSha.ToLowerInvariant()
            owner_token_sha256 = Get-Sha256Hex $token
            acquired_at_utc = $now.ToString('o')
            renewed_at_utc = $now.ToString('o')
            expires_at_utc = $now.AddSeconds($TtlSeconds).ToString('o')
        }
        Write-Lease $lease $newState
        $result = ConvertTo-PublicStatus ([pscustomobject]$newState)
        $result.owner_token = $token
        $result.recovered_expired_run_id = $expiredRunId
        $result | ConvertTo-Json -Compress
        return
    }

    if ($null -eq $state) { throw 'Qualification lease does not exist' }
    if ($state.run_id -cne $normalizedRunId) {
        throw 'Qualification lease is owned by another run'
    }
    if (-not $OwnerToken) { throw '-OwnerToken is required' }
    if (-not (Test-FixedHexEqual `
            (Get-Sha256Hex ($OwnerToken.ToUpperInvariant())) `
            ([string]$state.owner_token_sha256))) {
        throw 'Qualification lease owner token is invalid'
    }

    if ($Action -eq 'Renew') {
        if ((ConvertTo-UtcInstant $state.expires_at_utc) -le [DateTimeOffset]::UtcNow) {
            throw 'Expired qualification lease cannot be renewed; acquire a new lease'
        }
        $now = [DateTimeOffset]::UtcNow
        $updated = [ordered]@{
            schema = $state.schema
            run_id = $state.run_id
            role = $state.role
            machine = $state.machine
            peer_host = $state.peer_host
            git_sha = $state.git_sha
            owner_token_sha256 = $state.owner_token_sha256
            acquired_at_utc = $state.acquired_at_utc
            renewed_at_utc = $now.ToString('o')
            expires_at_utc = $now.AddSeconds($TtlSeconds).ToString('o')
        }
        Write-Lease $lease $updated
        ConvertTo-PublicStatus ([pscustomobject]$updated) | ConvertTo-Json -Compress
        return
    }

    Remove-Item -LiteralPath $lease -Force
    [ordered]@{
        released = -not (Test-Path -LiteralPath $lease)
        run_id = $normalizedRunId
        machine = [Environment]::MachineName.ToUpperInvariant()
    } | ConvertTo-Json -Compress
}
finally {
    if ($null -ne $lock) { $lock.Dispose() }
}
