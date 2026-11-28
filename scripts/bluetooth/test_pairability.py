import importlib.util
import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("manage_pairability.py")
SPEC = importlib.util.spec_from_file_location("manage_pairability", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeBluetoothApi:
    def __init__(self, connectable=False, discoverable=False):
        self.connectable = connectable
        self.discoverable = discoverable
        self.calls = []

    def is_connectable(self):
        return self.connectable

    def is_discoverable(self):
        return self.discoverable

    def set_connectable(self, enabled):
        self.calls.append(("connectable", enabled))
        self.connectable = enabled

    def set_discoverable(self, enabled):
        self.calls.append(("discoverable", enabled))
        self.discoverable = enabled


class PairabilityTests(unittest.TestCase):
    def test_interactive_policy_requires_human_consent(self):
        result = MODULE.assess_consent_policy(
            "windows-interactive",
            windows_iot_core=False,
            inbound_handler_registered=False,
        )
        self.assertTrue(result.supported)
        self.assertTrue(result.requires_human_consent)
        self.assertEqual(result.reason, "WINDOWS_DESKTOP_SYSTEM_CONSENT_REQUIRED")

    def test_unattended_policy_is_refused_on_windows_desktop(self):
        result = MODULE.assess_consent_policy(
            "unattended",
            windows_iot_core=False,
            inbound_handler_registered=False,
        )
        self.assertFalse(result.supported)
        self.assertFalse(result.requires_human_consent)
        self.assertEqual(
            result.reason,
            "UNATTENDED_INBOUND_PAIRING_REQUIRES_WINDOWS_IOT_CORE",
        )

    def test_unattended_policy_requires_an_implemented_iot_handler(self):
        result = MODULE.assess_consent_policy(
            "unattended",
            windows_iot_core=True,
            inbound_handler_registered=False,
        )
        self.assertFalse(result.supported)
        self.assertEqual(
            result.reason,
            "UNATTENDED_INBOUND_PAIRING_HANDLER_NOT_IMPLEMENTED",
        )

    def test_unattended_cli_refuses_before_touching_the_radio(self):
        output = io.StringIO()
        argv = [
            "manage_pairability.py",
            "--duration-seconds", "120",
            "--confirm-pairing-window",
            "--consent-policy", "unattended",
        ]
        with (
            patch.object(MODULE, "windows_is_iot_core", return_value=False),
            patch.object(MODULE, "WindowsBluetoothApi") as bluetooth_api,
            patch.object(sys, "argv", argv),
            redirect_stdout(output),
        ):
            self.assertEqual(MODULE.main(), 3)
        bluetooth_api.assert_not_called()
        self.assertIn('"event": "pairability-refused"', output.getvalue())

    @patch.object(MODULE.time, "sleep", return_value=None)
    def test_window_enables_then_restores_both_flags(self, _sleep):
        api = FakeBluetoothApi()
        initial, final = MODULE.pairing_window(api, 10)
        self.assertEqual((initial.connectable, initial.discoverable), (False, False))
        self.assertEqual((final.connectable, final.discoverable), (False, False))
        self.assertEqual(api.calls, [
            ("connectable", True),
            ("discoverable", True),
            ("discoverable", False),
            ("connectable", False),
        ])

    @patch.object(MODULE.time, "sleep", side_effect=KeyboardInterrupt)
    def test_window_restores_state_when_interrupted(self, _sleep):
        api = FakeBluetoothApi(connectable=True, discoverable=False)
        with self.assertRaises(KeyboardInterrupt):
            MODULE.pairing_window(api, 10)
        self.assertTrue(api.connectable)
        self.assertFalse(api.discoverable)
        self.assertEqual(api.calls, [("discoverable", True), ("discoverable", False)])


if __name__ == "__main__":
    unittest.main()
