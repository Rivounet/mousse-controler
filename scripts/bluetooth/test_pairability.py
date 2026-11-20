import importlib.util
from pathlib import Path
import sys
import unittest
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
