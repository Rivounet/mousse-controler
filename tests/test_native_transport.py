from pathlib import Path
import unittest
from unittest.mock import Mock

from mousse_controler.transport import NativeHogpTransport


class NativeHogpTransportCommandTests(unittest.TestCase):
    def test_packaged_alias_uses_microsoft_host_and_package_script(self) -> None:
        transport = NativeHogpTransport(Path("mousse-hogp-packaged.exe"))

        command = transport._engine_command()

        self.assertEqual(command[0], "mousse-hogp-packaged.exe")
        self.assertIn("-NoProfile", command)
        self.assertIn("-NonInteractive", command)
        self.assertIn("InstalledLocation.Path", command[-1])
        self.assertIn("hogp.ps1", command[-1])
        self.assertIn("-Stdio", command[-1])
        self.assertIn("[Console]::OutputEncoding=$utf8", command[-1])

    def test_status_parses_engine_detail(self) -> None:
        transport = NativeHogpTransport(Path("mousse-hogp-packaged.exe"))
        transport._command = Mock(return_value={
            "detail": "prepared=True,advertising=True,subscribed=False,buttons=0"
        })

        self.assertEqual(transport.status(), {
            "prepared": "True",
            "advertising": "True",
            "subscribed": "False",
            "buttons": "0",
        })

    def test_legacy_executable_keeps_direct_stdio_contract(self) -> None:
        executable = Path(r"C:\tools\mousse-hogp.exe")
        transport = NativeHogpTransport(executable)

        self.assertEqual(transport._engine_command(), [str(executable), "--stdio"])

    def test_deadlines_reject_unbounded_configuration(self) -> None:
        for kwargs in (
            {"startup_timeout": float("inf")},
            {"command_timeout": 11},
            {"stop_timeout": 0},
            {"termination_timeout": -1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                NativeHogpTransport(Path("engine.exe"), **kwargs)

    def test_powershell_engine_waits_for_advertising_to_stop(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("function Stop-AdvertisingAndWait", source)
        self.assertIn("advertising did not stop", source)

    def test_powershell_winrt_operations_have_explicit_deadline(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(
            encoding="utf-8")
        self.assertIn("[int]$TimeoutMilliseconds = 5000", source)
        self.assertIn("$task.Wait($TimeoutMilliseconds)", source)
        self.assertIn("WinRT operation timed out", source)
        self.assertIn("$Operation.Cancel()", source)

    def test_pairability_is_an_explicit_command_mode(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("@('start', 'pairable', 'stop')", source)
        self.assertIn("Incoming pairing is", source)
        self.assertIn("gated separately by the bounded OS pairability window", source)


if __name__ == "__main__":
    unittest.main()
