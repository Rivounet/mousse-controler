from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "runtime" / "controller_release.py"
SPEC = importlib.util.spec_from_file_location("controller_release", MODULE_PATH)
assert SPEC and SPEC.loader
controller_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller_release)
QualificationError = controller_release.QualificationError


class ControllerReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_root = ROOT.parents[1] / ".runtime-tests"
        temporary_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="mcr-", dir=temporary_root)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.releases = self.root / "releases"
        self.repository.mkdir()
        self.releases.mkdir()
        self.git("init")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "user.name", "Release Test")
        files = {
            "scripts/runtime/Start-MousseController.ps1": "# launcher\n",
            "scripts/runtime/controller_release.py": MODULE_PATH.read_text(encoding="utf-8"),
            "src/mousse_controler/app.py": "# application\n",
            "src/mousse_controler/controller.py": "# controller\n",
            "README.md": "not shipped\n",
        }
        for name, content in files.items():
            path = self.repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.sha = self.git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()
        try:
            Path(self.temporary.name).parent.rmdir()
        except OSError:
            pass

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_prepare_extracts_only_runtime_git_objects_and_is_reusable(self) -> None:
        result = controller_release.prepare_release(self.repository, self.sha, self.releases)
        release = Path(result["release"])

        verified = controller_release.verify_release(release)
        reused = controller_release.prepare_release(self.repository, self.sha, self.releases)

        self.assertEqual(result["status"], "PREPARED")
        self.assertEqual(reused["status"], "REUSED")
        self.assertEqual(verified["git_sha"], self.sha)
        self.assertFalse((release / "README.md").exists())
        completed = subprocess.run(
            [
                "python",
                "-B",
                str(release / "scripts" / "runtime" / "controller_release.py"),
                "verify",
                "--release",
                str(release),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_dirty_repository_is_refused(self) -> None:
        (self.repository / "README.md").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(QualificationError, "LOCAL_REPOSITORY_NOT_CLEAN"):
            controller_release.prepare_release(self.repository, self.sha, self.releases)

    def test_modified_or_extra_release_content_is_refused(self) -> None:
        result = controller_release.prepare_release(self.repository, self.sha, self.releases)
        release = Path(result["release"])
        target = release / "src" / "mousse_controler" / "app.py"
        original = target.read_bytes()
        target.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(QualificationError, "RELEASE_FILE_HASH_MISMATCH"):
            controller_release.verify_release(release)

        target.write_bytes(original)
        (release / "unexpected.txt").write_text("extra\n", encoding="utf-8")
        with self.assertRaisesRegex(QualificationError, "RELEASE_CONTENT_MISMATCH"):
            controller_release.verify_release(release)


if __name__ == "__main__":
    unittest.main()
