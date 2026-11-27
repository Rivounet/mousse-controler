#!/usr/bin/env python3
"""Local, non-material qualification entry point for Mousse-controler."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
WINDOWS_POWERSHELL = Path(
    os.environ.get("SystemRoot", r"C:\Windows")
) / "System32/WindowsPowerShell/v1.0/powershell.exe"
MINIMUM_PYTHON = (3, 12)
MATERIAL_EXCLUSIONS = (
    "scripts.bluetooth.test_diagnostics (3 tests; Windows radio diagnostics)",
    "scripts.diagnostics.test_inspect_monordinateur.TargetDiagnosticTests "
    "(4 tests; target/session diagnostics)",
    "all real Bluetooth, HID, capture, SSH, installation and deployment operations",
)
PROFILES = ("fast", "integration", "software", "build", "full-local")


@dataclass(frozen=True)
class Phase:
    name: str
    command: tuple[str, ...]
    category: str
    result_path: Path | None = None
    timeout_seconds: int = 900


class QualificationPreconditionError(RuntimeError):
    def __init__(self, message: str, git: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.git = git or {
            "commit": "unavailable",
            "tree": "unavailable",
            "branch": None,
            "clean": False,
        }


def _python(*arguments: str) -> tuple[str, ...]:
    return (sys.executable, *arguments)


def phases_for(profile: str, output_dir: Path) -> list[Phase]:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    fast_result = output_dir / "artifacts" / "fast-tests.json"
    integration_result = output_dir / "artifacts" / "integration-tests.json"
    fast = [
        Phase(
            "fast-tests",
            _python(
                "-B", str(ROOT / "scripts/qualification/run_software_tests.py"),
                "--tier", "fast", "--summary-path", str(fast_result),
            ),
            "software",
            fast_result,
            120,
        ),
    ]
    integration = [
        Phase(
            "integration-tests",
            _python(
                "-B", str(ROOT / "scripts/qualification/run_software_tests.py"),
                "--tier", "integration", "--summary-path", str(integration_result),
            ),
            "software",
            integration_result,
            600,
        ),
    ]
    software = fast + integration
    artifact_dir = output_dir / "artifacts" / "PositionAgent"
    manifest = output_dir / "artifacts" / "position-agent-build.json"
    build = [
        Phase(
            "python-compilation",
            _python("-m", "compileall", "-q", "-f", "src", "scripts", "tests"),
            "build",
        ),
        Phase(
            "api-reference-check",
            _python(str(ROOT / "scripts/generate_api_reference.py"), "--check"),
            "build",
        ),
        Phase(
            "powershell-syntax",
            (
                str(WINDOWS_POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "scripts/qualification/Test-PowerShellSyntax.ps1"),
                "-Root", str(ROOT),
            ),
            "build",
        ),
        Phase(
            "position-agent-build",
            (
                "pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
                str(ROOT / "scripts/build/Build-PositionAgent.ps1"),
                "-OutputDirectory", str(artifact_dir),
                "-QualificationManifestPath", str(manifest),
            ),
            "build",
        ),
    ]
    if profile == "fast":
        return fast
    if profile == "integration":
        return integration
    if profile == "software":
        return software
    if profile == "build":
        return build
    return software + build


def _tool_version(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=15, check=False,
        )
        return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _git(*arguments: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *arguments), cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise QualificationPreconditionError(f"Git is unavailable: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise QualificationPreconditionError(
            f"Git {' '.join(arguments)} failed: {detail}"
        )
    return completed.stdout.strip()


def _git_provenance() -> dict[str, object]:
    repository = Path(_git("rev-parse", "--show-toplevel")).resolve()
    if repository != ROOT.resolve():
        raise QualificationPreconditionError(
            f"qualification root {ROOT} does not match Git root {repository}"
        )
    commit = _git("rev-parse", "--verify", "HEAD^{commit}")
    tree = _git("rev-parse", "--verify", "HEAD^{tree}")
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", commit):
        raise QualificationPreconditionError(f"invalid Git commit identity: {commit!r}")
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", tree):
        raise QualificationPreconditionError(f"invalid Git tree identity: {tree!r}")
    branch = _git("branch", "--show-current") or None
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    git = {
        "commit": commit.lower(),
        "tree": tree.lower(),
        "branch": branch,
        "clean": not bool(status),
    }
    if status:
        raise QualificationPreconditionError(
            f"repository is dirty ({len(status.splitlines())} changed path(s))",
            git,
        )
    return git


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifacts(output_dir: Path) -> list[dict[str, object]]:
    artifact_root = output_dir / "artifacts"
    if not artifact_root.exists():
        return []
    return [
        {
            "path": str(path.relative_to(output_dir)),
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(artifact_root.rglob("*")) if path.is_file()
    ]


def _read_test_result(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"test result metadata is missing: {path.name}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("test result metadata must be a JSON object")
    required = {
        "schema", "tests_run", "failures", "errors", "skipped",
        "expected_failures", "unexpected_successes", "successful",
    }
    missing = sorted(required - result.keys())
    if missing:
        raise RuntimeError(f"test result metadata is incomplete: {', '.join(missing)}")
    if result["schema"] != "mousse-test-results-v1":
        raise RuntimeError("test result metadata has an unsupported schema")
    if int(result["tests_run"]) < 1:
        raise RuntimeError("test result metadata reports no executed tests")
    for counter in (
        "failures", "errors", "skipped", "expected_failures",
        "unexpected_successes",
    ):
        if int(result[counter]) != 0:
            raise RuntimeError(f"test result metadata reports {counter}")
    if not bool(result["successful"]):
        raise RuntimeError("test result metadata is not successful")
    return result


def run_qualification(
    profile: str,
    output_dir: Path,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
    git_provenance: Callable[[], dict[str, object]] = _git_provenance,
) -> tuple[int, dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    precondition_error: str | None = None
    try:
        git = git_provenance()
    except QualificationPreconditionError as exc:
        git = exc.git
        precondition_error = str(exc)
    summary: dict[str, object] = {
        "schema": "mousse-qualification-v2",
        "contract": "MC-ROBUSTNESS-R4-001",
        "profile": profile,
        "verdict": "PASS",
        "git_sha": git["commit"],
        "git": git,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "python_required": ">=3.12",
            "powershell": _tool_version(("pwsh", "--version")),
            "windows_powershell": _tool_version((
                str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            )),
            "git": _tool_version(("git", "--version")),
        },
        "exclusions": list(MATERIAL_EXCLUSIONS),
        "safety": {
            "material_diagnostics": False,
            "installation": False,
            "deployment": False,
            "remote_access": False,
        },
        "phases": [],
    }
    phase_results: list[dict[str, object]] = summary["phases"]  # type: ignore[assignment]
    exit_code = 0
    if precondition_error is not None:
        summary["verdict"] = "BLOCKED"
        summary["reason"] = precondition_error
        summary["duration_seconds"] = round(time.monotonic() - started, 3)
        summary["tests"] = {
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_successes": 0,
        }
        summary["artifacts"] = []
        summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return 2, summary
    if sys.version_info < MINIMUM_PYTHON:
        summary["verdict"] = "BLOCKED"
        summary["reason"] = (
            f"Python >= {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} required; "
            f"found {platform.python_version()}"
        )
        summary["duration_seconds"] = round(time.monotonic() - started, 3)
        summary["artifacts"] = []
        summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 2, summary
    temporary_parent = output_dir / ".temporary"
    temporary_parent.mkdir(exist_ok=True)
    # compileall mirrors each absolute source path below PYTHONPYCACHEPREFIX.
    # Keeping that prefix below the (possibly deep) qualification output can
    # exceed the classic Windows path limit before a single file is compiled.
    # Use the same short, worktree-local parent as the software test harness.
    short_temporary_parent = ROOT.parent / "t"
    short_temporary_parent.mkdir(exist_ok=True)
    try:
        with ExitStack() as stack:
            temporary = stack.enter_context(tempfile.TemporaryDirectory(
                prefix="r4-", dir=temporary_parent))
            pycache = stack.enter_context(tempfile.TemporaryDirectory(
                prefix="pyc-", dir=short_temporary_parent))
            environment = os.environ.copy()
            environment["MC_QUALIFICATION_TEMP"] = temporary
            environment["PYTHONPYCACHEPREFIX"] = pycache
            for phase in phases_for(profile, output_dir):
                phase_started = time.monotonic()
                log_path = output_dir / f"{phase.name}.log"
                executable = phase.command[0]
                resolved = executable if Path(executable).is_file() else which(executable)
                result: dict[str, object] = {
                    "name": phase.name,
                    "category": phase.category,
                    "status": "PASS",
                    "log": log_path.name,
                }
                phase_results.append(result)
                if not resolved:
                    result.update(status="BLOCKED", reason=f"required tool missing: {executable}")
                    log_path.write_text(str(result["reason"]) + "\n", encoding="utf-8")
                    summary["verdict"] = "BLOCKED"
                    exit_code = 2
                    break
                try:
                    with log_path.open("w", encoding="utf-8", errors="replace") as log_stream:
                        completed = command_runner(
                            phase.command, cwd=ROOT, env=environment, text=True,
                            stdout=log_stream, stderr=subprocess.STDOUT,
                            timeout=phase.timeout_seconds, check=False,
                        )
                        # Test doubles may return captured text instead of using the
                        # supplied stream. Real subprocesses stream directly so a
                        # verbose suite cannot fill a pipe and perturb timing tests.
                        if completed.stdout:
                            log_stream.write(completed.stdout)
                    result["exit_code"] = completed.returncode
                    if completed.returncode != 0:
                        result["status"] = "FAIL"
                        summary["verdict"] = "FAIL"
                        exit_code = 1
                        break
                    if phase.result_path:
                        result["tests"] = _read_test_result(phase.result_path)
                except KeyboardInterrupt:
                    result.update(status="INTERRUPTED", reason="qualification interrupted")
                    log_path.write_text("qualification interrupted\n", encoding="utf-8")
                    summary["verdict"] = "BLOCKED"
                    exit_code = 130
                    break
                except subprocess.TimeoutExpired as error:
                    result.update(status="FAIL", reason=f"phase timeout after {error.timeout}s")
                    log_path.write_text(str(result["reason"]) + "\n", encoding="utf-8")
                    summary["verdict"] = "FAIL"
                    exit_code = 1
                    break
                except Exception as error:
                    reason = f"{type(error).__name__}: {error}"
                    result.update(status="FAIL", reason=reason)
                    with log_path.open("a", encoding="utf-8", errors="replace") as log:
                        log.write(reason + "\n")
                    summary["verdict"] = "FAIL"
                    exit_code = 1
                    break
                finally:
                    result["duration_seconds"] = round(time.monotonic() - phase_started, 3)
    finally:
        shutil.rmtree(temporary_parent, ignore_errors=True)
        test_results = [
            phase["tests"] for phase in phase_results if "tests" in phase
        ]
        summary["tests"] = {
            key: sum(int(item.get(key, 0)) for item in test_results)
            for key in (
                "tests_run", "failures", "errors", "skipped",
                "expected_failures", "unexpected_successes",
            )
        }
        summary["duration_seconds"] = round(time.monotonic() - started, 3)
        summary["artifacts"] = _artifacts(output_dir)
        summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return exit_code, summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        help="log/artifact directory (default: out/qualification/<UTC timestamp>)",
    )
    arguments = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (arguments.output_dir or ROOT / "out" / "qualification" / stamp).resolve()
    code, summary = run_qualification(arguments.profile, output_dir)
    console = {
        "verdict": summary["verdict"],
        "profile": summary["profile"],
        "git_sha": summary["git_sha"],
        "git": summary["git"],
        "tests": summary.get("tests"),
        "duration_seconds": summary["duration_seconds"],
        "output_dir": str(output_dir),
        "exclusions": summary["exclusions"],
    }
    if "reason" in summary:
        console["reason"] = summary["reason"]
    print(json.dumps(console, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
