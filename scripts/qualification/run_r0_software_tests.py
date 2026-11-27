#!/usr/bin/env python3
"""Backward-compatible entry point for the tiered non-material test runner."""

from __future__ import annotations

import sys

from scripts.qualification.run_software_tests import main as tiered_main


def main() -> int:
    return tiered_main(["--tier", "all", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
