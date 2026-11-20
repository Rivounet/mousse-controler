from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StartupContractTests(unittest.TestCase):
    def test_runtime_advertises_after_preparing_gatt(self) -> None:
        source = (ROOT / "src" / "mousse_controler" / "app.py").read_text(encoding="utf-8")
        self.assertLess(source.index("controller.start()"), source.index("transport.advertise()"))

    def test_both_hosts_have_logon_startup_contracts(self) -> None:
        mini = (ROOT / "scripts" / "runtime" / "Manage-MousseControllerTask.ps1").read_text(encoding="utf-8")
        target = (ROOT / "scripts" / "target" / "Manage-InteractivePositionAgent.ps1").read_text(encoding="utf-8")
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", mini)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", target)
        self.assertIn("-RunLevel Limited", mini)


if __name__ == "__main__":
    unittest.main()
