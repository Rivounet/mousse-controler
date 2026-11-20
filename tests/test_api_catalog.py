from __future__ import annotations

from http.client import HTTPConnection
import json
from pathlib import Path
import threading
import time
import unittest

from mousse_controler.api_catalog import (
    ACTION_CONTRACTS,
    COMMAND_CONTRACTS,
    WEBSOCKET_EVENT_CONTRACTS,
    action_names,
    command_names,
    render_markdown_reference,
    validate_action_contract,
    validate_parameters,
    validate_registry,
)
from mousse_controler.command_server import CommandGateway, make_command_server
from mousse_controler.controller import MouseController, PositionStore
from mousse_controler.transport import SimulatedHidTransport


ROOT = Path(__file__).resolve().parents[1]


class ReceiverStub:
    def topology(self):
        raise AssertionError("catalog consultation must not inspect topology")

    def metrics(self):
        return {"accepted": 0}


class CaptureSpy:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def list_for_action(self, action_id: str):
        self.calls.append(("list", action_id))
        return []

    def delete(self, capture_id: str):
        self.calls.append(("delete", capture_id))
        return {}


class ApiCatalogTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedHidTransport()
        self.controller = MouseController(self.transport, PositionStore())
        self.captures = CaptureSpy()
        self.gateway = CommandGateway(
            b"token", self.controller, self.transport, ReceiverStub(),
            capture_broker=self.captures,
        )
        self.counter = 0

    def request(self, **arguments):
        self.counter += 1
        return self.gateway.execute({
            "command_id": f"catalog-{self.counter}",
            "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000,
            "command": "api_catalog",
            "arguments": arguments,
        })

    def test_registry_is_exhaustive_and_router_has_no_ghosts(self):
        expected = {
            "api_catalog", "advertise_start", "transport_status", "position_status",
            "position_metrics", "move", "click", "buttons", "scroll", "stop",
            "capabilities", "action_submit", "action_status", "action_list",
            "action_cancel", "action_pause", "action_resume", "action_continue",
            "action_events", "capture_status", "capture_delete", "sequence_start",
            "sequence_pause", "sequence_resume", "sequence_next", "sequence_skip",
            "sequence_stop", "sequence_status",
        }
        self.assertEqual(command_names(), expected)
        self.assertEqual(len(command_names()), 28)
        handlers = {contract["_handler"] for contract in COMMAND_CONTRACTS.values()}
        implemented = {
            name for name, value in CommandGateway.__dict__.items()
            if name.startswith("_command_") and callable(value)
        }
        self.assertEqual(handlers, implemented)
        for handler in handlers:
            self.assertTrue(callable(getattr(self.gateway, handler)))

    def test_action_types_and_websocket_events_are_complete(self):
        self.assertEqual(action_names(), {
            "move_relative", "move_to", "click", "press", "release", "hold", "drag",
            "move_with_buttons", "scroll", "wait", "wait_command", "sequence",
        })
        self.assertEqual(set(WEBSOCKET_EVENT_CONTRACTS), {
            "connected", "state", "control", "retry", "capture", "result",
        })

    def test_contracts_and_all_examples_are_valid(self):
        validate_registry()
        for contract in COMMAND_CONTRACTS.values():
            example = contract["examples"]["request"]
            self.assertEqual(example["command"], contract["name"])
            validate_parameters(example["arguments"], contract)
            self.assertIsInstance(contract["examples"]["response"], dict)
        for contract in ACTION_CONTRACTS.values():
            validate_action_contract(contract["examples"]["request_fragment"])

    def test_full_catalog_and_runtime_availability(self):
        result = self.request()
        self.assertEqual(result["counts"], {
            "commands": 28, "action_types": 12, "websocket_events": 6,
        })
        self.assertEqual(result["totals"], result["counts"])
        by_name = {item["name"]: item for item in result["commands"]}
        self.assertEqual(by_name["action_submit"]["availability"]["status"], "unavailable")
        self.assertEqual(by_name["capture_status"]["availability"]["status"], "available")
        self.assertTrue(all(item["availability"]["status"] == "unavailable"
                            for item in result["action_types"]))
        self.assertTrue(all(item["availability"]["status"] == "unavailable"
                            for item in result["websocket_events"]))
        self.assertEqual(set(result["action_execution"]["states"]), {
            "ACCEPTED", "RUNNING", "EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED",
        })
        self.assertNotIn("_handler", json.dumps(result))

    def test_name_category_and_section_filters(self):
        named = self.request(name="move", include=["commands"])
        self.assertEqual([item["name"] for item in named["commands"]], ["move"])
        self.assertEqual(named["counts"], {
            "commands": 1, "action_types": 0, "websocket_events": 0,
        })
        category = self.request(category="captures", include=["commands"])
        self.assertEqual({item["name"] for item in category["commands"]},
                         {"capture_status", "capture_delete"})
        actions = self.request(include=["action_types"])
        self.assertNotIn("commands", actions)
        self.assertEqual(actions["counts"]["action_types"], 12)

    def test_invalid_filters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown catalog command"):
            self.request(name="not_a_command")
        with self.assertRaisesRegex(ValueError, "unknown catalog category"):
            self.request(category="not_a_category")
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            self.request(include=["not_a_section"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.request(include=["commands", "commands"])

    def test_catalog_has_no_hid_or_capture_effect(self):
        before = list(self.transport.events)
        for arguments in ({}, {"name": "capture_delete"}, {"category": "mouse_legacy"}):
            self.request(**arguments)
        self.assertEqual(self.transport.events, before)
        self.assertEqual(self.captures.calls, [])

    def test_existing_command_accepts_undeclared_arguments_for_compatibility(self):
        result = self.gateway.execute({
            "command_id": "compat-capabilities",
            "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000,
            "command": "capabilities",
            "arguments": {"legacy_ignored": True},
        })
        self.assertTrue(result["accepted"])
        self.assertIn("buttons", result["capabilities"])

    def test_generated_reference_is_current(self):
        self.assertEqual(
            (ROOT / "docs" / "API-REFERENCE.md").read_text(encoding="utf-8"),
            render_markdown_reference(),
        )

    def test_http_authentication_is_still_required(self):
        server = make_command_server(0, self.gateway)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        payload = json.dumps({
            "command_id": "http-catalog",
            "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000,
            "command": "api_catalog",
            "arguments": {"include": ["commands"]},
        })
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request("POST", "/v1/command", payload,
                               {"Content-Type": "application/json"})
            self.assertEqual(connection.getresponse().status, 401)
            connection.close()

            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request("POST", "/v1/command", payload, {
                "Content-Type": "application/json", "Authorization": "Bearer token"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["counts"]["commands"], 28)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
