#!/usr/bin/env python3
"""Run explicitly tiered, non-material software tests with structured results."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
import tempfile
import time
import traceback
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
REMOTE = ROOT / "scripts" / "remote"


@dataclass(frozen=True)
class SuiteSpec:
    label: str
    directories: tuple[Path, ...] = ()
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class SuiteResult:
    label: str
    tests_run: int
    failures: int
    errors: int
    skipped: int
    expected_failures: int
    unexpected_successes: int
    successful: bool
    duration_seconds: float


TIERS: dict[str, tuple[SuiteSpec, ...]] = {
    "fast": (
        SuiteSpec("unit", directories=(ROOT / "tests" / "unit",)),
        SuiteSpec("contracts", directories=(ROOT / "tests" / "contract",)),
        SuiteSpec(
            "qualification-tooling",
            directories=(ROOT / "tests" / "qualification",),
        ),
    ),
    "integration": (
        SuiteSpec(
            "integration",
            directories=(ROOT / "tests" / "integration",),
        ),
        SuiteSpec(
            "remote-deployment-simulation",
            directories=(REMOTE,),
        ),
        SuiteSpec(
            "non-material-safety-contracts",
            names=(
                "scripts.bluetooth.test_pairability",
                "scripts.diagnostics.test_inspect_monordinateur.GattProbeSafetyTests",
            ),
        ),
    ),
}

MATERIAL_EXCLUSIONS = (
    "scripts.bluetooth.test_diagnostics (3 material diagnostics)",
    "scripts.diagnostics.test_inspect_monordinateur.TargetDiagnosticTests "
    "(4 target/session diagnostics)",
)


def _load(spec: SuiteSpec) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for directory in spec.directories:
        loader = unittest.TestLoader()
        if directory.is_relative_to(ROOT / "tests"):
            discovered = loader.discover(
                str(directory), pattern="test_*.py", top_level_dir=str(ROOT),
            )
        else:
            discovered = loader.discover(str(directory), pattern="test_*.py")
        suite.addTests(discovered)
    if spec.names:
        loader = unittest.TestLoader()
        suite.addTests(loader.loadTestsFromNames(spec.names))
    return suite


def _run(spec: SuiteSpec) -> SuiteResult:
    print(f"\n=== {spec.label} ===", flush=True)
    started = time.monotonic()
    try:
        result = unittest.TextTestRunner(verbosity=2).run(_load(spec))
    except Exception:
        traceback.print_exc()
        return SuiteResult(
            label=spec.label,
            tests_run=0,
            failures=0,
            errors=1,
            skipped=0,
            expected_failures=0,
            unexpected_successes=0,
            successful=False,
            duration_seconds=round(time.monotonic() - started, 3),
        )
    return SuiteResult(
        label=spec.label,
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures),
        unexpected_successes=len(result.unexpectedSuccesses),
        successful=result.wasSuccessful(),
        duration_seconds=round(time.monotonic() - started, 3),
    )


def _successful(suites: list[SuiteResult]) -> bool:
    return (
        all(item.successful for item in suites)
        and sum(item.skipped for item in suites) == 0
        and sum(item.expected_failures for item in suites) == 0
        and sum(item.unexpected_successes for item in suites) == 0
    )


def run_tier(tier: str) -> tuple[int, dict[str, object]]:
    if tier not in (*TIERS, "all"):
        raise ValueError(f"unknown test tier: {tier}")
    os.chdir(ROOT)
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    selected = tuple(TIERS) if tier == "all" else (tier,)
    specs = tuple(spec for current in selected for spec in TIERS[current])
    short_root = ROOT.parent / "t"
    short_root.mkdir(exist_ok=True)
    print("Material diagnostics excluded by construction:")
    for exclusion in MATERIAL_EXCLUSIONS:
        print(f"- {exclusion}")
    with tempfile.TemporaryDirectory(prefix="software-", dir=short_root) as temporary:
        prior = os.environ.get("MC_TEST_TMP")
        os.environ["MC_TEST_TMP"] = temporary
        try:
            suites = [_run(spec) for spec in specs]
        finally:
            if prior is None:
                os.environ.pop("MC_TEST_TMP", None)
            else:
                os.environ["MC_TEST_TMP"] = prior
    summary: dict[str, object] = {
        "schema": "mousse-test-results-v1",
        "tier": tier,
        "suites": [asdict(item) for item in suites],
        "tests_run": sum(item.tests_run for item in suites),
        "failures": sum(item.failures for item in suites),
        "errors": sum(item.errors for item in suites),
        "skipped": sum(item.skipped for item in suites),
        "expected_failures": sum(item.expected_failures for item in suites),
        "unexpected_successes": sum(item.unexpected_successes for item in suites),
        "material_diagnostics_excluded": 7,
    }
    summary["successful"] = _successful(suites)
    print(
        "\nSoftware tier {tier}: {tests} tests; failures: {failures}; errors: "
        "{errors}; skipped: {skipped}; expected failures: {expected}; "
        "unexpected successes: {unexpected}".format(
            tier=tier,
            tests=summary["tests_run"],
            failures=summary["failures"],
            errors=summary["errors"],
            skipped=summary["skipped"],
            expected=summary["expected_failures"],
            unexpected=summary["unexpected_successes"],
        )
    )
    return (0 if summary["successful"] else 1), summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=(*TIERS, "all"), default="all")
    parser.add_argument("--summary-path", type=Path)
    arguments = parser.parse_args(argv)
    code, summary = run_tier(arguments.tier)
    if arguments.summary_path:
        arguments.summary_path.parent.mkdir(parents=True, exist_ok=True)
        arguments.summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
