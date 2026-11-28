[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Install', 'Start', 'Status', 'Stop', 'Uninstall')]
    [string]$Action,
    [string]$SourceExecutablePath,
    [string]$SourceConfigPath,
    [string]$ExpectedExecutableSha256,
    [string]$ExpectedConfigSha256
)

$ErrorActionPreference = 'Stop'
$contract = 'MC-HOGP-NATIVE-OWNER-001'
$taskName = 'MousseControler-MC-HOGP-NATIVE-OWNER-001-ControlAgent'
$installDirectory = Join-Path $env:ProgramFiles "MousseControler\Qualification\$contract"
$configDirectory = Join-Path $env:ProgramData "MousseControler\Qualification\$contract"
$executablePath = Join-Path $installDirectory 'HogpControlAgent.exe'
$configPath = Join-Path $configDirectory 'hogp-control-agent.json'
$statePath = Join-Path $configDirectory 'agent-state.json'
$manifestPath = Join-Path $configDirectory 'install-manifest.json'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Administrator {
    if (-not (Test-Administrator)) {
        throw 'This one-time HOGP control-agent operation requires an elevated console'
    }
}

function Normalize-Sha256([string]$Value, [string]$Name) {
    $normalized = ($Value -replace '[:\s]', '').ToUpperInvariant()
    if ($normalized -notmatch '^[0-9A-F]{64}$') {
        throw "$Name must contain exactly 64 hexadecimal characters"
    }
    return $normalized
}

function Resolve-PrincipalSid([string]$Value) {
    if ($Value -match '^S-1-') {
        return [Security.Principal.SecurityIdentifier]::new($Value).Value
    }
    return ([Security.Principal.NTAccount]::new($Value).Translate(
        [Security.Principal.SecurityIdentifier])).Value
}

function Set-ProtectedDirectoryAcl([string]$Path, [switch]$AllowUsersRead) {
    $administrators = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
    $system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $users = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-545')
    $inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($administrators)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $system, 'FullControl', $inheritance, $propagation, 'Allow'))
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $administrators, 'FullControl', $inheritance, $propagation, 'Allow'))
    if ($AllowUsersRead) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
            $users, 'ReadAndExecute', $inheritance, $propagation, 'Allow'))
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Assert-ProtectedDirectory([string]$Path) {
    $administratorsSid = 'S-1-5-32-544'
    $systemSid = 'S-1-5-18'
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Protected path is not a regular directory: $Path"
    }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected -or
        (Resolve-PrincipalSid ([string]$acl.Owner)) -ne $administratorsSid) {
        throw "Protected path inheritance or owner is invalid: $Path"
    }
    $dangerousRights = (
        [Security.AccessControl.FileSystemRights]::WriteData -bor
        [Security.AccessControl.FileSystemRights]::AppendData -bor
        [Security.AccessControl.FileSystemRights]::WriteExtendedAttributes -bor
        [Security.AccessControl.FileSystemRights]::WriteAttributes -bor
        [Security.AccessControl.FileSystemRights]::Delete -bor
        [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
        [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
        [Security.AccessControl.FileSystemRights]::TakeOwnership
    )
    $allowedWriteSids = @($administratorsSid, $systemSid)
    foreach ($rule in @($acl.Access)) {
        if ($rule.AccessControlType -ne 'Allow' -or
            -not ($rule.FileSystemRights -band $dangerousRights)) {
            continue
        }
        $sid = $rule.IdentityReference.Translate(
            [Security.Principal.SecurityIdentifier]).Value
        if ($sid -notin $allowedWriteSids) {
            throw "Protected path grants mutation rights to an unexpected principal: $Path"
        }
    }
    foreach ($requiredSid in $allowedWriteSids) {
        $fullControl = @($acl.Access | Where-Object {
            $_.AccessControlType -eq 'Allow' -and
            $_.IdentityReference.Translate(
                [Security.Principal.SecurityIdentifier]).Value -eq $requiredSid -and
            ($_.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::FullControl) -eq
                [Security.AccessControl.FileSystemRights]::FullControl
        })
        if ($fullControl.Count -eq 0) {
            throw "Protected path is missing a required full-control principal: $Path"
        }
    }
}

function Get-ControlAgentProcessProbe {
    try {
        $processes = @(Get-CimInstance Win32_Process `
            -Filter "Name = 'HogpControlAgent.exe'" -ErrorAction Stop | Where-Object {
                $_.ExecutablePath -and
                [IO.Path]::GetFullPath($_.ExecutablePath).Equals(
                    [IO.Path]::GetFullPath($executablePath),
                    [StringComparison]::OrdinalIgnoreCase)
            })
        return [PSCustomObject]@{
            Available = $true
            ErrorType = $null
            Processes = $processes
        }
    } catch {
        return [PSCustomObject]@{
            Available = $false
            ErrorType = $_.Exception.GetType().Name
            Processes = @()
        }
    }
}

function Assert-TaskDefinition($Task, [string]$ExpectedPrincipalSid) {
    if (-not $Task -or $Task.Principal.RunLevel.ToString() -ne 'Highest' -or
        $Task.Principal.LogonType.ToString() -ne 'Interactive' -or
        @($Task.Actions).Count -ne 1) {
        throw 'HOGP control-agent task definition is invalid'
    }
    $action = $Task.Actions[0]
    $expectedArguments = '--config "{0}"' -f $configPath
    if (-not [IO.Path]::GetFullPath([string]$action.Execute).Equals(
            [IO.Path]::GetFullPath($executablePath),
            [StringComparison]::OrdinalIgnoreCase) -or
        [string]$action.Arguments -ne $expectedArguments -or
        -not [IO.Path]::GetFullPath([string]$action.WorkingDirectory).Equals(
            [IO.Path]::GetFullPath($installDirectory),
            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'HOGP control-agent task action does not match the protected installation'
    }
    if ((Resolve-PrincipalSid ([string]$Task.Principal.UserId)) -ne
        (Resolve-PrincipalSid $ExpectedPrincipalSid)) {
        throw 'HOGP control-agent task principal does not match the protected installation'
    }
    $triggers = @($Task.Triggers)
    if ($triggers.Count -ne 1 -or
        $triggers[0].CimClass.CimClassName -ne 'MSFT_TaskLogonTrigger' -or
        (Resolve-PrincipalSid ([string]$triggers[0].UserId)) -ne
            (Resolve-PrincipalSid $ExpectedPrincipalSid)) {
        throw 'HOGP control-agent task trigger does not match the protected installation'
    }
}

function Assert-InstallationIntegrity {
    Assert-ProtectedDirectory $installDirectory
    Assert-ProtectedDirectory $configDirectory
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'HOGP control-agent installation manifest is missing'
    }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.schema -ne 'mousse-hogp-control-install-v1' -or
        $manifest.contract -ne $contract -or
        -not (Test-Path -LiteralPath $executablePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
        throw 'HOGP control-agent installation manifest is invalid'
    }
    $expectedExe = Normalize-Sha256 ([string]$manifest.executable_sha256) 'manifest executable hash'
    $expectedConfig = Normalize-Sha256 ([string]$manifest.config_sha256) 'manifest config hash'
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $executablePath).Hash -ne $expectedExe -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $configPath).Hash -ne $expectedConfig) {
        throw 'HOGP control-agent protected installation hash mismatch'
    }
    if (-not $manifest.principal_sid) {
        throw 'HOGP control-agent installation principal is missing'
    }
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Assert-TaskDefinition $task ([string]$manifest.principal_sid)
}

function Get-ControlAgentState {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    $taskInfo = if ($task) {
        Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
    } else { $null }
    $processProbe = Get-ControlAgentProcessProbe
    $processes = @($processProbe.Processes)
    [ordered]@{
        contract = $contract
        task_name = $taskName
        task_present = ($null -ne $task)
        task_state = if ($task) { $task.State.ToString() } else { $null }
        task_run_level = if ($task) { $task.Principal.RunLevel.ToString() } else { $null }
        task_action_path = if ($task) { $task.Actions[0].Execute } else { $null }
        last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
        process_probe_available = $processProbe.Available
        process_probe_error_type = $processProbe.ErrorType
        agent_process_count = $processes.Count
        process_ids = @($processes | ForEach-Object { $_.ProcessId })
        executable_path = [IO.Path]::GetFullPath($executablePath)
        executable_sha256 = if (Test-Path -LiteralPath $executablePath -PathType Leaf) {
            (Get-FileHash -Algorithm SHA256 -LiteralPath $executablePath).Hash
        } else { $null }
        config_path = [IO.Path]::GetFullPath($configPath)
        config_sha256 = if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            (Get-FileHash -Algorithm SHA256 -LiteralPath $configPath).Hash
        } else { $null }
        manifest_present = (Test-Path -LiteralPath $manifestPath -PathType Leaf)
        state_present = (Test-Path -LiteralPath $statePath -PathType Leaf)
    }
}

function Wait-ControlAgentProcess([int]$ExpectedCount) {
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $processProbe = Get-ControlAgentProcessProbe
        if (-not $processProbe.Available) {
            throw "HOGP control-agent process inspection is unavailable: $($processProbe.ErrorType)"
        }
        $count = @($processProbe.Processes).Count
        if ($count -eq $ExpectedCount) { return }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Expected $ExpectedCount HOGP control-agent process, observed $count"
}

switch ($Action) {
    'Install' {
        Assert-Administrator
        if (-not $SourceExecutablePath -or -not $SourceConfigPath -or
            -not $ExpectedExecutableSha256 -or -not $ExpectedConfigSha256) {
            throw 'Install requires source paths and both expected SHA-256 values'
        }
        $expectedExe = Normalize-Sha256 $ExpectedExecutableSha256 'ExpectedExecutableSha256'
        $expectedConfig = Normalize-Sha256 $ExpectedConfigSha256 'ExpectedConfigSha256'
        foreach ($source in @($SourceExecutablePath, $SourceConfigPath)) {
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
                throw "Installation source not found: $source"
            }
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $SourceExecutablePath).Hash -ne $expectedExe -or
            (Get-FileHash -Algorithm SHA256 -LiteralPath $SourceConfigPath).Hash -ne $expectedConfig) {
            throw 'Installation source hash mismatch'
        }
        $candidateConfig = Get-Content -Raw -LiteralPath $SourceConfigPath | ConvertFrom-Json
        if (-not $candidateConfig.StatePath -or
            -not [IO.Path]::GetFullPath([string]$candidateConfig.StatePath).Equals(
                [IO.Path]::GetFullPath($statePath), [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Configuration StatePath does not target the protected qualification state file'
        }
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($existing -or (Test-Path -LiteralPath $executablePath) -or
            (Test-Path -LiteralPath $configPath) -or
            (Test-Path -LiteralPath $manifestPath)) {
            $state = Get-ControlAgentState
            if ($state.executable_sha256 -ne $expectedExe -or
                $state.config_sha256 -ne $expectedConfig -or -not $state.task_present) {
                throw 'A different control-agent installation already exists; uninstall it explicitly first'
            }
            Assert-InstallationIntegrity
            $state | ConvertTo-Json -Depth 5
            break
        }
        New-Item -ItemType Directory -Force -Path $installDirectory | Out-Null
        New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
        Set-ProtectedDirectoryAcl $installDirectory -AllowUsersRead
        Set-ProtectedDirectoryAcl $configDirectory
        Assert-ProtectedDirectory $installDirectory
        Assert-ProtectedDirectory $configDirectory
        $temporaryExe = Join-Path $installDirectory 'HogpControlAgent.exe.new'
        $temporaryConfig = Join-Path $configDirectory 'hogp-control-agent.json.new'
        Remove-Item -LiteralPath $temporaryExe -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $temporaryConfig -Force -ErrorAction SilentlyContinue
        $installationComplete = $false
        try {
        Copy-Item -LiteralPath $SourceExecutablePath -Destination $temporaryExe
        Copy-Item -LiteralPath $SourceConfigPath -Destination $temporaryConfig
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporaryExe).Hash -ne $expectedExe -or
            (Get-FileHash -Algorithm SHA256 -LiteralPath $temporaryConfig).Hash -ne $expectedConfig) {
            throw 'Staged installation hash mismatch'
        }
        Move-Item -LiteralPath $temporaryExe -Destination $executablePath
        Move-Item -LiteralPath $temporaryConfig -Destination $configPath
        $userIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $manifest = [ordered]@{
            schema = 'mousse-hogp-control-install-v1'
            contract = $contract
            executable_sha256 = $expectedExe
            config_sha256 = $expectedConfig
            principal_sid = $userIdentity.User.Value
        }
        $manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $arguments = '--config "{0}"' -f $configPath
        $taskAction = New-ScheduledTaskAction -Execute $executablePath `
            -Argument $arguments -WorkingDirectory $installDirectory
        $userId = $userIdentity.Name
        $principal = New-ScheduledTaskPrincipal -UserId $userId `
            -LogonType Interactive -RunLevel Highest
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -MultipleInstances IgnoreNew -RestartCount 5 `
            -RestartInterval (New-TimeSpan -Minutes 1)
        Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $trigger `
            -Principal $principal -Settings $settings | Out-Null
        Assert-InstallationIntegrity
        Start-ScheduledTask -TaskName $taskName
        Wait-ControlAgentProcess 1
        Get-ControlAgentState | ConvertTo-Json -Depth 5
        $installationComplete = $true
        } finally {
            if (-not $installationComplete) {
                try {
                    $failedTask = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
                    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false `
                        -ErrorAction SilentlyContinue
                } catch { }
                foreach ($path in @(
                    $temporaryExe, $temporaryConfig, $executablePath, $configPath,
                    $statePath, $manifestPath
                )) {
                    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    'Start' {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if (-not $task) { throw 'HOGP control-agent task is not installed' }
        Assert-InstallationIntegrity
        Start-ScheduledTask -TaskName $taskName
        Wait-ControlAgentProcess 1
        Get-ControlAgentState | ConvertTo-Json -Depth 5
    }
    'Status' {
        Get-ControlAgentState | ConvertTo-Json -Depth 5
    }
    'Stop' {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) { Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue }
        Wait-ControlAgentProcess 0
        Get-ControlAgentState | ConvertTo-Json -Depth 5
    }
    'Uninstall' {
        Assert-Administrator
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            Wait-ControlAgentProcess 0
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        }
        foreach ($path in @($executablePath, $configPath, $statePath, $manifestPath)) {
            if (Test-Path -LiteralPath $path -PathType Leaf) {
                Remove-Item -LiteralPath $path -Force
            }
        }
        foreach ($directory in @($installDirectory, $configDirectory)) {
            if ((Test-Path -LiteralPath $directory -PathType Container) -and
                @(Get-ChildItem -LiteralPath $directory -Force).Count -eq 0) {
                Remove-Item -LiteralPath $directory -Force
            }
        }
        Get-ControlAgentState | ConvertTo-Json -Depth 5
    }
}
