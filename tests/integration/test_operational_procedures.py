from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = ROOT / "scripts" / "operations"
POWERSHELL = shutil.which("pwsh")


def run_powershell(command: str) -> subprocess.CompletedProcess[str]:
    if not POWERSHELL:
        raise unittest.SkipTest("PowerShell 7 is required")
    return subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def parse_json_output(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    output = completed.stdout.strip()
    if not output:
        raise AssertionError(f"PowerShell returned no JSON: {completed.stderr}")
    return json.loads(output)


class OperationalProcedureContractTests(unittest.TestCase):
    def test_controller_manager_resolves_relative_python_to_absolute_path(self) -> None:
        manager = ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1"
        script = str(manager).replace("'", "''")
        command = rf"""
. '{script}' -LibraryOnly
$resolved = Resolve-PythonExecutable 'python.exe'
[ordered]@{{
    rooted = [IO.Path]::IsPathRooted($resolved)
    exists = Test-Path -LiteralPath $resolved -PathType Leaf
}} | ConvertTo-Json -Compress
"""
        completed = run_powershell(command)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual({"rooted": True, "exists": True}, parse_json_output(completed))

    def test_controller_task_stop_continues_after_emergency_stop_error(self) -> None:
        manager = ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1"
        with tempfile.TemporaryDirectory(prefix="mc-task-stop-") as temporary:
            config = Path(temporary) / "controller.json"
            config.write_text("{}", encoding="utf-8")
            script = str(manager).replace("'", "''")
            fixture = str(config).replace("'", "''")
            command = rf"""
. '{script}' -LibraryOnly
$script:events = [Collections.Generic.List[string]]::new()
function Stop-ScheduledTask {{
    [CmdletBinding()] param([string]$TaskName)
    $script:events.Add('task-stop')
}}
function Start-Sleep {{
    [CmdletBinding()] param([int]$Milliseconds)
    $script:events.Add('bounded-wait')
}}
function Get-CimInstance {{
    [CmdletBinding()] param([string]$ClassName, [string]$Filter)
    @()
}}
function Unregister-ScheduledTask {{
    [CmdletBinding(SupportsShouldProcess = $true)] param([string]$TaskName)
    $script:events.Add('task-unregister')
}}
$arguments = '-File "' + $launcher + '" -ConfigPath "{fixture}" -PythonPath "python.exe"'
$task = [pscustomobject]@{{
    Actions = @([pscustomobject]@{{ Execute = 'powershell.exe'; Arguments = $arguments }})
}}
Stop-ManagedRuntime $task -EmergencyStopCommand {{
    param($Python, $Config)
    $script:events.Add('emergency-stop')
    throw 'simulated command failure'
}}
[ordered]@{{ events = @($script:events) }} | ConvertTo-Json -Compress
"""
            completed = run_powershell(command)
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = parse_json_output(completed)
        self.assertEqual(
            ["emergency-stop", "task-stop", "bounded-wait", "task-unregister"],
            payload["events"],
        )

    def test_complete_procedure_set_is_present(self) -> None:
        expected = {
            "Check-CodexEnvironment.ps1",
            "Inspect-LocalRuntime.ps1",
            "Inspect-RemoteTarget.ps1",
            "Invoke-BuildAndQualify.ps1",
            "Prepare-MsixSigning.ps1",
            "Prepare-Deployment.ps1",
            "README.md",
        }
        self.assertEqual(expected, {path.name for path in OPERATIONS.iterdir()})

    def test_project_rule_uses_only_exact_approved_channels(self) -> None:
        rule = (ROOT / ".cursor" / "rules" / "mousse-operations.mdc").read_text(
            encoding="utf-8"
        )
        self.assertTrue(rule.startswith("---\n"))
        self.assertIn("alwaysApply: true", rule)
        self.assertIn("monordinateur-pv-mig.conf MonOrdinateur", rule)
        self.assertIn("schtasks.exe /Query /TN \\MousseControler-HOGP", rule)
        self.assertNotRegex(rule, r"allow.*(?:ssh|PowerShell).*(?:all|arbitrary)")

    def test_inspectors_are_read_only(self) -> None:
        forbidden = re.compile(
            r"\b(?:Register-ScheduledTask|Set-ScheduledTask|Start-ScheduledTask|"
            r"Unregister-ScheduledTask|Set-Acl|New-SelfSignedCertificate|"
            r"Import-Certificate|Add-AppxPackage|Remove-AppxPackage)\b",
            re.IGNORECASE,
        )
        for name in ("Inspect-LocalRuntime.ps1", "Inspect-RemoteTarget.ps1"):
            with self.subTest(name=name):
                source = (OPERATIONS / name).read_text(encoding="utf-8")
                self.assertIsNone(forbidden.search(source))
                self.assertIn("effects = 'read-only'", source)

    def test_signing_never_installs_trust_or_package(self) -> None:
        source = (OPERATIONS / "Prepare-MsixSigning.ps1").read_text(encoding="utf-8")
        for forbidden in (
            "Import-Certificate",
            "Add-AppxPackage",
            "Remove-AppxPackage",
            "Register-ScheduledTask",
            "Set-ScheduledTask",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("Windows DPAPI CurrentUser", source)
        self.assertIn("CN=MousseControler", source)
        self.assertIn("trust_store_modified = $false", source)

    def _local_runtime_payload(self, process_query: str) -> dict[str, object]:
        script = str(OPERATIONS / "Inspect-LocalRuntime.ps1").replace("'", "''")
        command = rf"""
. '{script}' -LibraryOnly
$inspection = Get-LocalProcessInspection -ProcessQuery {{ {process_query} }}
$principal = [pscustomobject]@{{ LogonType = 3; RunLevel = 0 }}
$definition = [pscustomobject]@{{ Principal = $principal }}
$task = [pscustomobject]@{{
    Enabled = $true; State = 3; LastRunTime = [datetime]::MinValue
    LastTaskResult = 1; Definition = $definition
}}
$payload = New-LocalRuntimePayload -Task $task -Actions @() -Triggers @() `
    -DefinitionHash $null -ProcessInspection $inspection -CommandPortOpen $false `
    -Name '\MousseControler-HOGP'
[ordered]@{{
    payload = $payload
    exit_code = Get-LocalRuntimeExitCode $inspection
}} | ConvertTo-Json -Depth 9 -Compress
"""
        completed = run_powershell(command)
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = parse_json_output(completed)
        payload = result["payload"]
        payload["_test_exit_code"] = result["exit_code"]
        return payload

    def test_local_process_inspection_failure_is_blocked_and_unknown(self) -> None:
        payload = self._local_runtime_payload(
            "throw [UnauthorizedAccessException]::new('provider denied')"
        )
        self.assertEqual("BLOCKED", payload["status"])
        runtime = payload["runtime"]
        self.assertEqual("BLOCKED", runtime["inspection_status"])
        self.assertEqual("UnauthorizedAccessException", runtime["inspection_error_type"])
        self.assertIsNone(runtime["matching_process_count"])
        self.assertIsNone(runtime["processes"])
        self.assertEqual(2, payload["_test_exit_code"])

    def test_local_process_inspection_success_reports_verified_count(self) -> None:
        payload = self._local_runtime_payload(
            "[pscustomobject]@{ CommandLine = 'Start-MousseController.ps1'; "
            "ProcessId = 42; SessionId = 1; ExecutablePath = 'powershell.exe' }"
        )
        self.assertEqual("PASS", payload["status"])
        runtime = payload["runtime"]
        self.assertEqual("PASS", runtime["inspection_status"])
        self.assertEqual(1, runtime["matching_process_count"])
        self.assertEqual(42, runtime["processes"][0]["process_id"])
        self.assertEqual(0, payload["_test_exit_code"])

    def test_local_process_inspection_verified_empty_is_zero_not_unknown(self) -> None:
        payload = self._local_runtime_payload("$null")
        self.assertEqual("PASS", payload["status"])
        runtime = payload["runtime"]
        self.assertEqual("PASS", runtime["inspection_status"])
        self.assertEqual(0, runtime["matching_process_count"])
        self.assertEqual([], runtime["processes"])

    def _deployment_result(
        self,
        *,
        evidence_sha: str | None = None,
        evidence_identity: str = "Rivounet.MousseControler.Hogp",
        evidence_version: str = "1.0.0.3",
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        with tempfile.TemporaryDirectory(prefix="mc-deployment-") as temporary:
            fixture = Path(temporary)
            package = fixture / "qualification.msix"
            manifest = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">
  <Identity Name="Rivounet.MousseControler.Hogp" Publisher="CN=MousseControler"
            Version="1.0.0.3" ProcessorArchitecture="x64" />
</Package>
"""
            with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("AppxManifest.xml", manifest)
                archive.writestr("payload.bin", b"qualified fixture")
            digest = hashlib.sha256(package.read_bytes()).hexdigest().upper()
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                text=True, encoding="utf-8", check=True,
            ).stdout.strip()
            qualification = fixture / "summary.json"
            qualification.write_text(
                json.dumps({"verdict": "PASS", "git_sha": head}), encoding="utf-8"
            )
            signing = fixture / "signing.json"
            signing.write_text(json.dumps({
                "status": "PASS",
                "signature": {"signer_matches_key": True},
                "package": {
                    "sha256": evidence_sha or digest,
                    "size": package.stat().st_size,
                    "identity_name": evidence_identity,
                    "publisher": "CN=MousseControler",
                    "version": evidence_version,
                },
            }), encoding="utf-8")
            script = OPERATIONS / "Prepare-Deployment.ps1"
            if not POWERSHELL:
                raise unittest.SkipTest("PowerShell 7 is required")
            completed = subprocess.run(
                [
                    POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
                    "-File", str(script), "-QualificationSummary", str(qualification),
                    "-PackagePath", str(package), "-SigningEvidence", str(signing),
                    "-ExpectedGitSha", head,
                ],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30, check=False,
            )
            return completed, parse_json_output(completed)

    def test_deployment_accepts_evidence_matching_exact_package(self) -> None:
        _, payload = self._deployment_result()
        self.assertTrue(payload["checks"]["signing_qualified"])
        self.assertEqual("Rivounet.MousseControler.Hogp", payload["package"]["identity_name"])
        self.assertEqual("1.0.0.3", payload["package"]["version"])

    def test_deployment_rejects_mismatched_hash(self) -> None:
        completed, payload = self._deployment_result(evidence_sha="0" * 64)
        self.assertEqual(2, completed.returncode)
        self.assertEqual("PARTIAL", payload["status"])
        self.assertFalse(payload["checks"]["signing_qualified"])

    def test_deployment_rejects_mismatched_identity(self) -> None:
        completed, payload = self._deployment_result(evidence_identity="Other.Package")
        self.assertEqual(2, completed.returncode)
        self.assertEqual("PARTIAL", payload["status"])
        self.assertFalse(payload["checks"]["signing_qualified"])

    def test_deployment_rejects_mismatched_version(self) -> None:
        completed, payload = self._deployment_result(evidence_version="1.0.0.4")
        self.assertEqual(2, completed.returncode)
        self.assertEqual("PARTIAL", payload["status"])
        self.assertFalse(payload["checks"]["signing_qualified"])

    def test_each_entry_point_has_versioned_contract_and_interrupt_code(self) -> None:
        for path in sorted(OPERATIONS.glob("*.ps1")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("MC-CODEX-ENVIRONMENT-001/", source)
                self.assertIn("exit 130", source)


if __name__ == "__main__":
    unittest.main()
