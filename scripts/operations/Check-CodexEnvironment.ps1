[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Get-ToolState([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    [ordered]@{ available = [bool]$command; kind = if ($command) { $command.CommandType.ToString() } else { $null } }
}

try {
    $head = (& git -C $root rev-parse HEAD 2>$null)
    $gitReady = $LASTEXITCODE -eq 0
    $status = if ($gitReady) { @(& git -C $root status --short) } else { @() }
    $checks = [ordered]@{
        repository = [ordered]@{ available = $gitReady; clean = $gitReady -and $status.Count -eq 0; head = if ($gitReady) { $head.Trim() } else { $null } }
        tools = [ordered]@{
            git = Get-ToolState 'git'
            python = Get-ToolState 'python'
            pwsh = Get-ToolState 'pwsh'
            windows_powershell = [ordered]@{ available = Test-Path -LiteralPath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -PathType Leaf }
            ssh = [ordered]@{ available = Test-Path -LiteralPath "$env:SystemRoot\System32\OpenSSH\ssh.exe" -PathType Leaf }
            schtasks = [ordered]@{ available = Test-Path -LiteralPath "$env:SystemRoot\System32\schtasks.exe" -PathType Leaf }
        }
        qualified_inputs = [ordered]@{
            ssh_config = Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.ssh\monordinateur-pv-mig.conf') -PathType Leaf
            task_definition = Test-Path -LiteralPath 'C:\ProgramData\MousseControler\MousseControler-HOGP.task.xml' -PathType Leaf
            runtime_config = Test-Path -LiteralPath 'C:\ProgramData\MousseControler\controller.json' -PathType Leaf
        }
        boundaries = [ordered]@{
            sandbox_network_restricted = $true
            system_providers_may_require_exact_outside_approval = $true
            interactive_session_not_implied_by_ssh = $true
        }
    }
    $required = @(
        $checks.repository.available,
        $checks.tools.git.available,
        $checks.tools.python.available,
        $checks.tools.pwsh.available,
        $checks.tools.windows_powershell.available,
        $checks.tools.ssh.available,
        $checks.tools.schtasks.available,
        $checks.qualified_inputs.ssh_config,
        $checks.qualified_inputs.runtime_config
    )
    $ready = -not ($required -contains $false)
    [ordered]@{
        contract = 'MC-CODEX-ENVIRONMENT-001/check-environment-v1'
        status = if ($ready) { 'READY' } else { 'BLOCKED' }
        checks = $checks
    } | ConvertTo-Json -Depth 8
    if (-not $ready) { exit 2 }
} catch [Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [ordered]@{ contract = 'MC-CODEX-ENVIRONMENT-001/check-environment-v1'; status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json
    exit 1
}
