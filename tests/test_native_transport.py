from pathlib import Path
import unittest

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

    def test_legacy_executable_keeps_direct_stdio_contract(self) -> None:
        executable = Path(r"C:\tools\mousse-hogp.exe")
        transport = NativeHogpTransport(executable)

        self.assertEqual(transport._engine_command(), [str(executable), "--stdio"])

    def test_powershell_engine_waits_for_advertising_to_stop(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("function Stop-AdvertisingAndWait", source)
        self.assertIn("advertising did not stop", source)

    def test_pairability_is_an_explicit_command_mode(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("@('start', 'pairable', 'stop')", source)
        self.assertIn("Incoming pairing is", source)
        self.assertIn("gated separately by the bounded OS pairability window", source)


if __name__ == "__main__":
    unittest.main()
