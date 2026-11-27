#!/usr/bin/env python3
"""Backward-compatible entry point for the tiered non-material test runner."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qualification.run_software_tests import main as tiered_main


def main() -> int:
    return tiered_main(["--tier", "all", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
