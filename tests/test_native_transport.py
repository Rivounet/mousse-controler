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


if __name__ == "__main__":
    unittest.main()
