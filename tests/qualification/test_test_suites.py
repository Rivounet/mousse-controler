from __future__ import annotations

import unittest

from scripts.qualification import run_software_tests as runner


def _test_ids(suite: unittest.TestSuite) -> set[str]:
    result: set[str] = set()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            result.update(_test_ids(item))
        else:
            result.add(item.id())
    return result


class TestSuiteArchitectureTests(unittest.TestCase):
    def test_fast_and_integration_tiers_are_nonempty_and_disjoint(self) -> None:
        fast = set().union(*(
            _test_ids(runner._load(spec)) for spec in runner.TIERS["fast"]
        ))
        integration = set().union(*(
            _test_ids(runner._load(spec)) for spec in runner.TIERS["integration"]
        ))
        self.assertGreater(len(fast), 100)
        self.assertGreater(len(integration), 100)
        self.assertFalse(fast & integration)
        self.assertFalse(any("test_diagnostics" in item for item in fast | integration))
        self.assertFalse(any("TargetDiagnosticTests" in item for item in fast | integration))

    def test_skips_and_expected_failures_are_not_qualification_success(self) -> None:
        base = runner.SuiteResult(
            label="fixture", tests_run=1, failures=0, errors=0, skipped=0,
            expected_failures=0, unexpected_successes=0, successful=True,
            duration_seconds=0.0,
        )
        self.assertTrue(runner._successful([base]))
        self.assertFalse(runner._successful([
            runner.SuiteResult(**{**base.__dict__, "skipped": 1})
        ]))
        self.assertFalse(runner._successful([
            runner.SuiteResult(**{**base.__dict__, "expected_failures": 1})
        ]))
