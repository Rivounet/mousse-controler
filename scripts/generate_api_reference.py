#!/usr/bin/env python3
"""Generate or verify the API reference committed from the runtime registry."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mousse_controler.api_catalog import render_markdown_reference  # noqa: E402


TARGET = ROOT / "docs" / "API-REFERENCE.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    args = parser.parse_args()
    expected = render_markdown_reference()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != expected:
            print(f"stale generated reference: {TARGET}", file=sys.stderr)
            return 1
        print(f"API reference is current: {TARGET}")
        return 0
    TARGET.write_text(expected, encoding="utf-8")
    print(f"generated {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
