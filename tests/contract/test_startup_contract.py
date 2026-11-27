import math
from pathlib import Path
import unittest

from mousse_controler.app import _bounded_interval


ROOT = Path(__file__).resolve().parents[2]


class StartupContractTests(unittest.TestCase):
    def test_hogp_maintenance_intervals_are_finite_and_bounded(self) -> None:
        self.assertEqual(30.0, _bounded_interval({}, "interval", 30.0, 60.0))
        self.assertEqual(0.1, _bounded_interval({"interval": 0.1}, "interval", 30.0, 60.0))
        for invalid in (0, -1, 61, math.nan, math.inf, -math.inf):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    _bounded_interval({"interval": invalid}, "interval", 30.0, 60.0)

    def test_runtime_advertises_after_preparing_gatt(self) -> None:
        source = (ROOT / "src" / "mousse_controler" / "app.py").read_text(encoding="utf-8")
        self.assertLess(source.index("controller.start()"), source.index("transport.advertise()"))

    def test_both_hosts_have_logon_startup_contracts(self) -> None:
        mini = (ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1").read_text(encoding="utf-8")
        target = (ROOT / "scripts" / "target" / "Manage-InteractivePositionAgent.ps1").read_text(encoding="utf-8")
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", mini)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", target)
        self.assertIn("-RunLevel Limited", mini)
        for source in (mini, target):
            self.assertIn("-RestartCount 5", source)
            self.assertIn("-RestartInterval (New-TimeSpan -Minutes 1)", source)

    def test_mini_task_stop_releases_hid_and_removes_only_managed_child(self) -> None:
        mini = (ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1").read_text(encoding="utf-8")
        self.assertIn("mousse_controler.command_client", mini)
        self.assertIn("Refusing to stop unrelated task", mini)
        self.assertIn("Get-CimInstance Win32_Process", mini)
        self.assertIn("mousse_controler.app serve --config", mini)
        self.assertIn("Stop-Process -Id $process.ProcessId", mini)

    def test_mini_launcher_retries_transient_startup_failures(self) -> None:
        launcher = (ROOT / "scripts" / "runtime" / "Start-MousseController.ps1").read_text(encoding="utf-8")
        self.assertIn("$MaximumAttempts = 5", launcher)
        self.assertIn("$RetryDelaySeconds = 30", launcher)
        self.assertIn("Start-Sleep -Seconds $RetryDelaySeconds", launcher)

    def test_scheduled_runtime_requires_verified_immutable_release(self) -> None:
        manager = (ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1").read_text(
            encoding="utf-8"
        )
        launcher = (ROOT / "scripts" / "runtime" / "Start-MousseController.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("-ReleasePath is required for Start", manager)
        self.assertIn("AllowLegacyTaskMigration", manager)
        self.assertIn("managedParent -ne $legacyWorktrees", manager)
        self.assertIn("controller_release.py", manager)
        self.assertIn("verify --release", manager)
        self.assertIn("Mutable source launch refused", launcher)
        self.assertIn("Controller release integrity verification failed", launcher)

    def test_runtime_cleans_transport_when_initialization_fails(self) -> None:
        source = (ROOT / "src" / "mousse_controler" / "app.py").read_text(encoding="utf-8")
        startup = source[source.index("controller = MouseController"):
                         source.index("def serve_position_only")]
        self.assertIn("lifecycle = _RuntimeLifecycle", startup)
        self.assertIn("except BaseException as exc:", startup)
        self.assertIn("cleanup_errors = lifecycle.close()", startup)
        self.assertIn("controller.emergency_stop", source)


if __name__ == "__main__":
    unittest.main()
