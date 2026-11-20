#!/usr/bin/env python3
"""Run the software-only R0 baseline while explicitly excluding material diagnostics."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
REMOTE = ROOT / "scripts" / "remote"
EXCLUDED_MATERIAL = (
    "scripts.bluetooth.test_diagnostics (3 tests; invokes Windows radio diagnostics)",
    "scripts.diagnostics.test_inspect_monordinateur.TargetDiagnosticTests "
    "(4 tests; invokes the target/session diagnostic)",
)


def run(label: str, suite: unittest.TestSuite) -> tuple[bool, int, int]:
    print(f"\n=== {label} ===", flush=True)
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful(), count, len(result.expectedFailures)


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    loader = unittest.TestLoader()
    suites = [
        ("core + R0 characterization", loader.discover(str(ROOT / "tests"),
                                                        pattern="test_*.py")),
        ("remote/deployment simulation", loader.discover(str(REMOTE),
                                                          pattern="test_*.py")),
        ("non-material safety contracts", loader.loadTestsFromNames([
            "scripts.bluetooth.test_pairability",
            "scripts.diagnostics.test_inspect_monordinateur.GattProbeSafetyTests",
        ])),
    ]
    print("Material diagnostics excluded by construction:")
    for item in EXCLUDED_MATERIAL:
        print(f"- {item}")
    # Release tests intentionally enforce the Windows deployment path budget.
    # Keep their qualification root short even when the host TEMP path belongs
    # to a deeply nested sandbox package.
    short_root = ROOT.parent / "t"
    short_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="r0-", dir=short_root) as temporary:
        os.environ["MC_TEST_TMP"] = temporary
        results = [run(label, suite) for label, suite in suites]
    total = sum(count for _ok, count, _xfail in results)
    expected = sum(xfail for _ok, _count, xfail in results)
    print(f"\nR0 software total: {total}; expected failures: {expected}; "
          f"material diagnostics excluded: 7")
    return 0 if all(ok for ok, _count, _xfail in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
