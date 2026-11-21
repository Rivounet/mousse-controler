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
PROFILES = ("software", "build", "full-local")


@dataclass(frozen=True)
class Phase:
    name: str
    command: tuple[str, ...]
    category: str


def _python(*arguments: str) -> tuple[str, ...]:
    return (sys.executable, *arguments)


def phases_for(profile: str, output_dir: Path) -> list[Phase]:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    software = [
        Phase(
            "software-tests",
            _python("-B", str(ROOT / "scripts/qualification/run_r0_software_tests.py")),
            "software",
        ),
    ]
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


def _git_sha() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


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


def run_qualification(
    profile: str,
    output_dir: Path,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
    git_sha: Callable[[], str] = _git_sha,
) -> tuple[int, dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    summary: dict[str, object] = {
        "contract": "MC-ROBUSTNESS-R4-001",
        "profile": profile,
        "verdict": "PASS",
        "git_sha": git_sha(),
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
                            timeout=1800, check=False,
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
                finally:
                    result["duration_seconds"] = round(time.monotonic() - phase_started, 3)
    finally:
        shutil.rmtree(temporary_parent, ignore_errors=True)
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
    print(json.dumps({
        "verdict": summary["verdict"],
        "profile": summary["profile"],
        "git_sha": summary["git_sha"],
        "duration_seconds": summary["duration_seconds"],
        "output_dir": str(output_dir),
        "exclusions": summary["exclusions"],
    }, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
