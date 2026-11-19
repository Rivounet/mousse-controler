"""Test package bootstrap for the repository's src layout."""

from pathlib import Path
import sys


SOURCE = str(Path(__file__).resolve().parents[1] / "src")
if SOURCE not in sys.path:
    sys.path.insert(0, SOURCE)
