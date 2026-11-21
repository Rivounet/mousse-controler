[CmdletBinding()]
param(
    [string]$SshPath = "$env:SystemRoot\System32\OpenSSH\ssh.exe",
    [string]$SshConfig = (Join-Path $env:USERPROFILE '.ssh\monordinateur-pv-mig.conf'),
    [string]$Alias = 'MonOrdinateur',
    [string]$TaskName = 'MousseControler-PositionAgent'
)

$ErrorActionPreference = 'Stop'
if ($Alias -ne 'MonOrdinateur') { throw 'Only the qualified MonOrdinateur alias is accepted.' }
if ($TaskName -ne 'MousseControler-PositionAgent') { throw 'Only the qualified PositionAgent task is accepted.' }
if ([IO.Path]::GetFullPath($SshPath) -ne [IO.Path]::GetFullPath("$env:SystemRoot\System32\OpenSSH\ssh.exe")) {
    throw 'Only the qualified Windows OpenSSH binary is accepted.'
}
if ([IO.Path]::GetFullPath($SshConfig) -ne [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.ssh\monordinateur-pv-mig.conf'))) {
    throw 'Only the qualified dedicated SSH configuration is accepted.'
}
if (-not (Test-Path -LiteralPath $SshConfig -PathType Leaf)) { throw 'Dedicated SSH configuration is missing.' }

$remoteScript = @'
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$taskName = 'MousseControler-PositionAgent'
try {
    $scheduler = New-Object -ComObject 'Schedule.Service'
    $scheduler.Connect()
    $task = $scheduler.GetFolder('\').GetTask($taskName)
    $definition = $task.Definition
    $action = @($definition.Actions)[0]
    $program = [Environment]::ExpandEnvironmentVariables([string]$action.Path)
    $programHash = if ($program -and (Test-Path -LiteralPath $program -PathType Leaf)) {
        (Get-FileHash -LiteralPath $program -Algorithm SHA256).Hash
    } else { $null }
    $leaf = if ($program) { [IO.Path]::GetFileName($program) } else { $null }
    $processes = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $leaf -and $_.Name -eq $leaf
    } | ForEach-Object {
        [ordered]@{ process_id = $_.ProcessId; session_id = $_.SessionId; executable_sha256 = if ($_.ExecutablePath -and (Test-Path -LiteralPath $_.ExecutablePath)) { (Get-FileHash -LiteralPath $_.ExecutablePath -Algorithm SHA256).Hash } else { $null } }
    })
    $os = Get-CimInstance Win32_OperatingSystem
    [ordered]@{
        status = 'PASS'
        os = [ordered]@{ caption = $os.Caption; build = $os.BuildNumber }
        task = [ordered]@{
            name = $taskName
            enabled = $task.Enabled
            state = $task.State
            last_run_utc = if ($task.LastRunTime -gt [datetime]::MinValue) { $task.LastRunTime.ToUniversalTime().ToString('o') } else { $null }
            last_result = $task.LastTaskResult
            principal = [ordered]@{ logon_type = $definition.Principal.LogonType; run_level = $definition.Principal.RunLevel }
            program_leaf = $leaf
            program_exists = [bool]($program -and (Test-Path -LiteralPath $program -PathType Leaf))
            program_sha256 = $programHash
        }
        runtime = [ordered]@{ process_count = $processes.Count; processes = $processes }
    } | ConvertTo-Json -Depth 8 -Compress
} catch {
    [ordered]@{ status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json -Compress
    exit 1
}
'@

try {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remoteScript))
    $raw = @(& $SshPath -F $SshConfig $Alias 'powershell.exe' '-NoLogo' '-NoProfile' '-NonInteractive' '-EncodedCommand' $encoded 2>&1 | ForEach-Object { [string]$_ })
    $sshExit = $LASTEXITCODE
    $jsonLine = $raw | Where-Object { $_.TrimStart().StartsWith('{') } | Select-Object -Last 1
    if (-not $jsonLine) { throw "Remote command produced no structured result (ssh exit $sshExit)." }
    $payload = $jsonLine | ConvertFrom-Json
    [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/inspect-remote-target-v1'
        status = if ($sshExit -eq 0 -and $payload.status -eq 'PASS') { 'PASS' } else { 'FAIL' }
        channel = [ordered]@{ alias = $Alias; strict_host_identity = $true; sandbox = $false }
        target = $payload
        effects = 'read-only'
    } | ConvertTo-Json -Depth 10
    if ($sshExit -ne 0 -or $payload.status -ne 'PASS') { exit 1 }
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/inspect-remote-target-v1'; status = 'BLOCKED'; boundary = 'exact-outside-sandbox-ssh'; error = $_.Exception.Message } | ConvertTo-Json
    exit 2
}
