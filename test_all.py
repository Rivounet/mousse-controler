"""Make the complete test suite discoverable from the repository root."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
REMOTE = ROOT / "scripts" / "remote"
BLUETOOTH = ROOT / "scripts" / "bluetooth"
DIAGNOSTICS = ROOT / "scripts" / "diagnostics"
SRC = ROOT / "src"


def load_tests(loader, standard_tests, pattern):
    # The historical command-line scripts deliberately use sibling imports so
    # that they remain directly executable. Add their folder just for tests.
    sys.path.insert(0, str(REMOTE))
    sys.path.insert(0, str(SRC))
    suite = loader.suiteClass()
    suite.addTests(
        loader.discover(
            str(REMOTE), pattern="test_*.py", top_level_dir=str(REMOTE)
        )
    )
    suite.addTests(
        loader.discover(
            str(BLUETOOTH), pattern="test_*.py", top_level_dir=str(BLUETOOTH)
        )
    )
    suite.addTests(
        loader.discover(
            str(DIAGNOSTICS), pattern="test_*.py", top_level_dir=str(DIAGNOSTICS)
        )
    )
    return suite
