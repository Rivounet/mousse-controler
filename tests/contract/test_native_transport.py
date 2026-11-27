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

    def test_packaged_engine_receives_normalized_authorized_client(self) -> None:
        client = "ab" * 32
        transport = NativeHogpTransport(
            Path("mousse-hogp-packaged.exe"),
            authorized_client_sha256=client,
        )

        self.assertIn(
            "-AuthorizedClientSha256 '" + client.upper() + "'",
            transport._engine_command()[-1],
        )

    def test_qualification_alias_is_a_packaged_engine_with_authorization(self) -> None:
        transport = NativeHogpTransport(
            Path("mousse-hogp-qualification.exe"),
            authorized_client_sha256="A" * 64,
        )

        command = transport._engine_command()
        self.assertEqual(command[0], "mousse-hogp-qualification.exe")
        self.assertIn("InstalledLocation.Path", command[-1])
        self.assertIn("-AuthorizedClientSha256 '" + "A" * 64 + "'", command[-1])

    def test_authorized_client_identity_is_fail_closed(self) -> None:
        for invalid in ("", "0" * 63, "G" * 64):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                NativeHogpTransport(
                    Path("mousse-hogp-packaged.exe"),
                    authorized_client_sha256=invalid,
                )
        with self.assertRaisesRegex(ValueError, "packaged WinRT engine"):
            NativeHogpTransport(
                Path("legacy.exe"), authorized_client_sha256="0" * 64,
            )

    def test_status_parses_engine_detail(self) -> None:
        transport = NativeHogpTransport(Path("mousse-hogp-packaged.exe"))
        transport._command = Mock(return_value={
            "detail": (
                "prepared=True,advertising=True,subscribed=True,"
                "authorized_subscriber=False,subscriber_count=1,"
                "subscriber_id_sha256=ABC,subscriber_session_status=Active,buttons=0"
            )
        })

        self.assertEqual(transport.status(), {
            "prepared": "True",
            "advertising": "True",
            "subscribed": "True",
            "authorized_subscriber": "False",
            "subscriber_count": "1",
            "subscriber_id_sha256": "ABC",
            "subscriber_session_status": "Active",
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
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("function Stop-AdvertisingAndWait", source)
        self.assertIn("advertising did not stop", source)

    def test_powershell_winrt_operations_have_explicit_deadline(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(
            encoding="utf-8")
        self.assertIn("[int]$TimeoutMilliseconds = 5000", source)
        self.assertIn("$task.Wait($TimeoutMilliseconds)", source)
        self.assertIn("WinRT operation timed out", source)
        self.assertIn("$Operation.Cancel()", source)

    def test_pairability_is_an_explicit_command_mode(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(encoding="utf-8")
        self.assertIn("@('start', 'pairable', 'stop')", source)
        self.assertIn("Incoming pairing is", source)
        self.assertIn("gated separately by the bounded OS pairability window", source)

    def test_powershell_engine_targets_one_authorized_subscriber(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "hogp-powershell" / "hogp.ps1").read_text(
            encoding="utf-8")
        self.assertIn("expected exactly one subscribed HID host", source)
        self.assertIn("subscribed HID host is not authorized", source)
        self.assertIn("@($bufferType, $subscribedClientType)", source)
        self.assertIn("authorized_subscriber=", source)


if __name__ == "__main__":
    unittest.main()
