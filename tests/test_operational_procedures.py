from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ROOT / "scripts" / "operations"


class OperationalProcedureContractTests(unittest.TestCase):
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

    def test_each_entry_point_has_versioned_contract_and_interrupt_code(self) -> None:
        for path in sorted(OPERATIONS.glob("*.ps1")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("MC-CODEX-ENVIRONMENT-001/", source)
                self.assertIn("exit 130", source)


if __name__ == "__main__":
    unittest.main()
