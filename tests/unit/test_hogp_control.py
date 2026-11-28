import json
import time
import unittest

from mousse_controler.hogp_control import (
    HogpControlCoordinator,
    HogpControlPolicy,
    HogpControlReceiver,
)
from mousse_controler.security import HmacVerifier, sign


TARGET_AEP = "A" * 64
ADAPTER = "B" * 64
PAIRED_PNP = "C" * 64
HID_PNP = "D" * 64
GENERATION = "11111111-1111-4111-8111-111111111111"


def report(**changes):
    value = {
        "schema": "mousse-hogp-control-v1",
        "provider_generation": None,
        "target_aep_sha256": TARGET_AEP,
        "adapter_instance_sha256": ADAPTER,
        "paired_pnp_instance_sha256": PAIRED_PNP,
        "hid_pnp_instance_sha256": HID_PNP,
        "radio_present": True,
        "radio_state": "On",
        "adapter_problem_code": 0,
        "paired": True,
        "hid_present": False,
        "elevated": True,
        "acknowledgment": None,
    }
    value.update(changes)
    return value


class HogpControlCoordinatorTests(unittest.TestCase):
    def coordinator(
        self, *, status=None, clock_ms=None, monotonic_ms=None, **policy_changes,
    ):
        values = {
            "target_key_id": "hogp-agent",
            "target_aep_sha256": TARGET_AEP,
            "adapter_instance_sha256": ADAPTER,
            "paired_pnp_instance_sha256": PAIRED_PNP,
            "hid_pnp_instance_sha256": HID_PNP,
            "allow_adapter_restart": True,
            "allow_endpoint_restart": True,
            "command_cooldown_seconds": 30,
        }
        values.update(policy_changes)
        transport_status = status or (lambda: {
            "authorized_subscriber": "False",
            "subscriber_count": "0",
            "advertising": "True",
        })
        return HogpControlCoordinator(
            HogpControlPolicy(**values),
            transport_status,
            provider_generation=GENERATION,
            clock_ms=clock_ms or (lambda: 1_000_000),
            monotonic_ms=monotonic_ms or clock_ms or (lambda: 1_000_000),
        )

    def test_first_report_observes_generation_without_recovery(self) -> None:
        response = self.coordinator().accept("hogp-agent", report())

        self.assertEqual(response["provider_generation"], GENERATION)
        self.assertIsNone(response["command"])

    def test_generation_change_requests_one_endpoint_restart(self) -> None:
        coordinator = self.coordinator()

        first = coordinator.accept(
            "hogp-agent",
            report(provider_generation="22222222-2222-4222-8222-222222222222"),
        )
        command = first["command"]
        self.assertEqual(command["action"], "restart_paired_endpoint")

        acknowledged = coordinator.accept(
            "hogp-agent",
            report(
                provider_generation="22222222-2222-4222-8222-222222222222",
                acknowledgment={
                    "command_id": command["command_id"],
                    "state": "executed",
                },
            ),
        )
        self.assertIsNone(acknowledged["command"])
        self.assertEqual(acknowledged["last_acknowledgment"]["state"], "executed")

    def test_unknown_command_outcome_is_acknowledged_without_replay(self) -> None:
        coordinator = self.coordinator()
        issued = coordinator.accept(
            "hogp-agent",
            report(provider_generation="22222222-2222-4222-8222-222222222222"),
        )

        acknowledged = coordinator.accept(
            "hogp-agent",
            report(
                provider_generation=GENERATION,
                acknowledgment={
                    "command_id": issued["command"]["command_id"],
                    "state": "outcome_unknown",
                },
            ),
        )

        self.assertIsNone(acknowledged["command"])
        self.assertEqual(
            acknowledged["last_acknowledgment"]["state"], "outcome_unknown",
        )

    def test_recovery_no_longer_required_is_acknowledged_without_replay(self) -> None:
        coordinator = self.coordinator()
        issued = coordinator.accept(
            "hogp-agent",
            report(provider_generation="22222222-2222-4222-8222-222222222222"),
        )

        acknowledged = coordinator.accept(
            "hogp-agent",
            report(
                provider_generation=GENERATION,
                acknowledgment={
                    "command_id": issued["command"]["command_id"],
                    "state": "not_required",
                },
            ),
        )

        self.assertIsNone(acknowledged["command"])
        self.assertEqual(
            acknowledged["last_acknowledgment"]["state"], "not_required",
        )

    def test_provider_rotation_invalidates_old_commands_and_changes_generation(self) -> None:
        coordinator = self.coordinator()
        old = coordinator.accept(
            "hogp-agent",
            report(provider_generation="22222222-2222-4222-8222-222222222222"),
        )

        rotated = coordinator.rotate_provider_generation(
            "33333333-3333-4333-8333-333333333333",
        )
        current = coordinator.accept("hogp-agent", report(provider_generation=GENERATION))

        self.assertIsNotNone(old["command"])
        self.assertEqual(rotated, "33333333-3333-4333-8333-333333333333")
        self.assertEqual(current["provider_generation"], rotated)
        self.assertIsNone(current["last_acknowledgment"])

    def test_radio_off_is_observable_but_never_restarts_the_wrong_node(self) -> None:
        response = self.coordinator().accept(
            "hogp-agent",
            report(radio_state="Off"),
        )

        self.assertIsNone(response["command"])

    def test_persistent_missing_hid_recovers_after_target_agent_restart(self) -> None:
        now = [1_000_000]
        coordinator = self.coordinator(clock_ms=lambda: now[0])

        first = coordinator.accept("hogp-agent", report(provider_generation=None))
        now[0] += 31_000
        second = coordinator.accept("hogp-agent", report(provider_generation=GENERATION))

        self.assertIsNone(first["command"])
        self.assertEqual(second["command"]["action"], "restart_paired_endpoint")

    def test_recovery_cooldown_uses_monotonic_time(self) -> None:
        wall = [1_000_000]
        monotonic = [1_000_000]
        coordinator = self.coordinator(
            clock_ms=lambda: wall[0],
            monotonic_ms=lambda: monotonic[0],
        )
        first = coordinator.accept(
            "hogp-agent",
            report(
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
            ),
        )
        coordinator.rotate_provider_generation(
            "33333333-3333-4333-8333-333333333333",
        )
        wall[0] -= 3_600_000
        monotonic[0] += 31_000

        second = coordinator.accept(
            "hogp-agent",
            report(
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
            ),
        )

        self.assertEqual(first["command"]["action"], "restart_bluetooth_adapter")
        self.assertEqual(second["command"]["action"], "restart_bluetooth_adapter")

    def test_code_43_requests_adapter_restart_even_on_first_report(self) -> None:
        response = self.coordinator().accept(
            "hogp-agent",
            report(radio_present=False, radio_state="Unavailable", adapter_problem_code=43),
        )

        self.assertEqual(response["command"]["action"], "restart_bluetooth_adapter")

    def test_connected_transport_suppresses_recovery(self) -> None:
        coordinator = self.coordinator(status=lambda: {
            "authorized_subscriber": "True",
            "subscriber_count": "1",
            "advertising": "True",
        })

        response = coordinator.accept(
            "hogp-agent",
            report(
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
                provider_generation="22222222-2222-4222-8222-222222222222",
            ),
        )

        self.assertIsNone(response["command"])
        self.assertTrue(response["transport"]["authorized_subscriber"])

    def test_transport_status_failure_is_fail_closed(self) -> None:
        def unavailable():
            raise RuntimeError("engine unavailable")

        coordinator = self.coordinator(status=unavailable)

        response = coordinator.accept(
            "hogp-agent",
            report(radio_present=False, radio_state="Unavailable", adapter_problem_code=43),
        )

        self.assertFalse(response["transport"]["available"])
        self.assertIsNone(response["command"])

    def test_malformed_transport_status_is_fail_closed(self) -> None:
        for malformed in (
            None,
            {},
            {"advertising": "maybe", "authorized_subscriber": "False"},
            {"advertising": "True"},
        ):
            with self.subTest(malformed=malformed):
                coordinator = self.coordinator(status=lambda: malformed)
                response = coordinator.accept(
                    "hogp-agent",
                    report(
                        radio_present=False,
                        radio_state="Unavailable",
                        adapter_problem_code=43,
                    ),
                )

                self.assertFalse(response["transport"]["available"])
                self.assertFalse(response["transport"]["authorized_subscriber"])
                self.assertIsNone(response["command"])

    def test_provider_not_advertising_never_triggers_target_recovery(self) -> None:
        coordinator = self.coordinator(status=lambda: {
            "advertising": "False",
            "authorized_subscriber": "False",
            "subscriber_count": "0",
        })

        response = coordinator.accept(
            "hogp-agent",
            report(
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
            ),
        )

        self.assertTrue(response["transport"]["available"])
        self.assertIsNone(response["command"])

    def test_outstanding_command_is_suspended_while_provider_is_unhealthy(self) -> None:
        status = [{
            "advertising": "True",
            "authorized_subscriber": "False",
            "subscriber_count": "0",
        }]
        coordinator = self.coordinator(status=lambda: status[0])
        issued = coordinator.accept(
            "hogp-agent",
            report(provider_generation="22222222-2222-4222-8222-222222222222"),
        )

        status[0] = {}
        unavailable = coordinator.accept("hogp-agent", report(provider_generation=GENERATION))
        status[0] = {
            "advertising": "False",
            "authorized_subscriber": "False",
            "subscriber_count": "0",
        }
        not_advertising = coordinator.accept(
            "hogp-agent", report(provider_generation=GENERATION),
        )
        status[0] = {
            "advertising": "True",
            "authorized_subscriber": "False",
            "subscriber_count": "0",
        }
        resumed = coordinator.accept("hogp-agent", report(provider_generation=GENERATION))

        self.assertIsNotNone(issued["command"])
        self.assertIsNone(unavailable["command"])
        self.assertIsNone(not_advertising["command"])
        self.assertEqual(
            resumed["command"]["command_id"], issued["command"]["command_id"],
        )

    def test_non_elevated_agent_never_receives_pnp_command(self) -> None:
        response = self.coordinator().accept(
            "hogp-agent",
            report(
                elevated=False,
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
                provider_generation="22222222-2222-4222-8222-222222222222",
            ),
        )

        self.assertIsNone(response["command"])

    def test_identity_or_key_mismatch_is_rejected(self) -> None:
        coordinator = self.coordinator()
        with self.assertRaisesRegex(ValueError, "unauthorized key"):
            coordinator.accept("position-agent", report())
        with self.assertRaisesRegex(ValueError, "AEP identity mismatch"):
            coordinator.accept("hogp-agent", report(target_aep_sha256="D" * 64))

    def test_actions_are_disabled_by_default_policy(self) -> None:
        policy = HogpControlPolicy(
            target_key_id="hogp-agent",
            target_aep_sha256=TARGET_AEP,
            adapter_instance_sha256=ADAPTER,
            paired_pnp_instance_sha256=PAIRED_PNP,
            hid_pnp_instance_sha256=HID_PNP,
        )
        coordinator = HogpControlCoordinator(
            policy,
            lambda: {"authorized_subscriber": "False"},
            provider_generation=GENERATION,
            clock_ms=lambda: 1_000_000,
        )

        response = coordinator.accept(
            "hogp-agent",
            report(
                radio_present=False,
                radio_state="Unavailable",
                adapter_problem_code=43,
                provider_generation="22222222-2222-4222-8222-222222222222",
            ),
        )

        self.assertIsNone(response["command"])


class HogpControlReceiverTests(unittest.TestCase):
    def test_receiver_reuses_hmac_and_replay_protection(self) -> None:
        secret = b"control-secret"
        verifier = HmacVerifier({"hogp-agent": secret})
        coordinator = HogpControlCoordinator(
            HogpControlPolicy(
                target_key_id="hogp-agent",
                target_aep_sha256=TARGET_AEP,
                adapter_instance_sha256=ADAPTER,
                paired_pnp_instance_sha256=PAIRED_PNP,
                hid_pnp_instance_sha256=HID_PNP,
            ),
            lambda: {"authorized_subscriber": "False"},
            provider_generation=GENERATION,
        )
        receiver = HogpControlReceiver(verifier, coordinator)
        body = json.dumps(report(), separators=(",", ":")).encode()
        now = int(time.time() * 1000)
        headers = {
            "X-Agent-Key": "hogp-agent",
            "X-Timestamp": str(now),
            "X-Sequence": "1",
            "X-Signature": sign(
                secret, "POST", "/v1/hogp-control", now, 1, body,
            ),
        }

        accepted = receiver.accept(
            headers, body, "/v1/hogp-control",
        )

        self.assertEqual(accepted["schema"], "mousse-hogp-control-v1")
        self.assertEqual(accepted["accepted_seq"], 1)
        with self.assertRaises(ValueError):
            receiver.accept(headers, body, "/v1/hogp-control")


if __name__ == "__main__":
    unittest.main()
