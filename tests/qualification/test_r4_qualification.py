from __future__ import annotations

import importlib
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.qualification import qualify


class QualificationProfileTests(unittest.TestCase):
    def test_profiles_are_local_and_exclude_material_and_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for profile in qualify.PROFILES:
                phases = qualify.phases_for(profile, output)
                rendered = " ".join(" ".join(phase.command) for phase in phases).lower()
                self.assertNotIn("scripts\\diagnostics", rendered)
                self.assertNotIn("scripts/diagnostics", rendered)
                self.assertNotIn("bluetooth\\test_diagnostics", rendered)
                self.assertNotIn("monordinateur", rendered)
                self.assertNotIn("update-interactivepositionagent", rendered)
                self.assertNotIn("manage-moussecontrollertask", rendered)
                self.assertNotIn("ssh", rendered)
            self.assertEqual(
                [phase.name for phase in qualify.phases_for("fast", output)],
                ["fast-tests"],
            )
            self.assertEqual(
                [phase.name for phase in qualify.phases_for("integration", output)],
                ["integration-tests"],
            )
            self.assertEqual(
                [phase.name for phase in qualify.phases_for("software", output)],
                ["fast-tests", "integration-tests"],
            )
            self.assertEqual(
                [phase.name for phase in qualify.phases_for("full-local", output)],
                ["fast-tests", "integration-tests", "test-architecture-measurement",
                 "python-compilation", "api-reference-check", "powershell-syntax",
                 "position-agent-build", "pairing-tool-build", "mouse-witness-build",
                 "hogp-package-build"],
            )

    def test_build_profile_only_builds_into_qualification_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            phases = qualify.phases_for("build", output)
            build_phases = [
                phase for phase in phases if "-OutputDirectory" in phase.command
            ]
            self.assertEqual(
                [phase.name for phase in build_phases],
                ["position-agent-build", "pairing-tool-build", "mouse-witness-build",
                 "hogp-package-build"],
            )
            for phase in phases:
                with self.subTest(phase=phase.name):
                    self.assertNotIn("Install", phase.command)
                    if phase.required_artifact is not None:
                        self.assertTrue(phase.required_artifact.is_relative_to(output))
            for phase in build_phases:
                output_argument = Path(
                    phase.command[phase.command.index("-OutputDirectory") + 1]
                )
                self.assertTrue(output_argument.is_relative_to(output))

    def test_profile_definition_survives_fresh_process_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            before = qualify.phases_for("full-local", output)
            reloaded = importlib.reload(qualify)
            after = reloaded.phases_for("full-local", output)
            self.assertEqual([asdict(phase) for phase in before],
                             [asdict(phase) for phase in after])


class QualificationOutcomeTests(unittest.TestCase):
    PROVENANCE = {
        "commit": "a" * 40,
        "tree": "b" * 40,
        "branch": "test/mc-test-strategy-001",
        "clean": True,
    }

    @staticmethod
    def _success(command, **_kwargs):
        if "--output" in command:
            path = Path(command[command.index("--output") + 1])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        if "--summary-path" in command:
            path = Path(command[command.index("--summary-path") + 1])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "schema": "mousse-test-results-v1",
                "tests_run": 1,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "expected_failures": 0,
                "unexpected_successes": 0,
                "successful": True,
            }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="ok\n")

    def test_missing_required_tool_is_blocked_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            code, summary = qualify.run_qualification(
                "build", output, command_runner=self._success,
                which=lambda tool: None if tool == "pwsh" else tool,
                git_provenance=lambda: self.PROVENANCE,
            )
            self.assertEqual(code, 2)
            self.assertEqual(summary["verdict"], "BLOCKED")
            self.assertEqual(summary["phases"][-1]["status"], "BLOCKED")

    def test_failed_test_produces_failure_and_sha_and_exclusions(self):
        def fail(command, **_kwargs):
            return subprocess.CompletedProcess(command, 17, stdout="deliberate failure\n")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            code, summary = qualify.run_qualification(
                "software", output, command_runner=fail,
                git_provenance=lambda: self.PROVENANCE,
            )
            self.assertEqual(code, 1)
            self.assertEqual(summary["verdict"], "FAIL")
            self.assertEqual(summary["git_sha"], "a" * 40)
            self.assertEqual(summary["git"]["tree"], "b" * 40)
            self.assertEqual(summary["exclusions"], list(qualify.MATERIAL_EXCLUSIONS))
            self.assertIn("deliberate failure", (output / "fast-tests.log").read_text())

    def test_interruption_is_observable_and_temporary_files_are_cleaned(self):
        def interrupt(_command, **kwargs):
            Path(kwargs["env"]["MC_QUALIFICATION_TEMP"], "marker").write_text("temporary")
            raise KeyboardInterrupt

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            code, summary = qualify.run_qualification(
                "software", output, command_runner=interrupt,
                git_provenance=lambda: self.PROVENANCE,
            )
            self.assertEqual(code, 130)
            self.assertEqual(summary["verdict"], "BLOCKED")
            self.assertEqual(summary["phases"][0]["status"], "INTERRUPTED")
            self.assertFalse((output / ".temporary").exists())
            self.assertTrue((output / "summary.json").is_file())

    def test_pycache_prefix_uses_short_worktree_local_directory_and_is_cleaned(self):
        observed: dict[str, Path] = {}

        def capture_environment(command, **kwargs):
            observed["pycache"] = Path(kwargs["env"]["PYTHONPYCACHEPREFIX"])
            return self._success(command, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "deep" / "qualification" / "result"
            code, summary = qualify.run_qualification(
                "software", output, command_runner=capture_environment,
                git_provenance=lambda: self.PROVENANCE,
            )
            self.assertEqual(code, 0)
            self.assertEqual(summary["verdict"], "PASS")
            self.assertEqual(observed["pycache"].parent,
                             qualify.ROOT.parent / "t")
            self.assertFalse(observed["pycache"].exists())
            self.assertFalse((output / ".temporary").exists())

    def test_dirty_repository_is_blocked_before_any_phase(self):
        calls = []

        def dirty():
            raise qualify.QualificationPreconditionError(
                "repository is dirty (1 changed path(s))",
                {**self.PROVENANCE, "clean": False},
            )

        def should_not_run(*_args, **_kwargs):
            calls.append(True)
            raise AssertionError("phase must not run")

        with tempfile.TemporaryDirectory() as temporary:
            code, summary = qualify.run_qualification(
                "fast", Path(temporary) / "result",
                command_runner=should_not_run, git_provenance=dirty,
            )
        self.assertEqual(2, code)
        self.assertEqual("BLOCKED", summary["verdict"])
        self.assertFalse(summary["git"]["clean"])
        self.assertEqual([], calls)

    def test_unavailable_git_identity_is_blocked_not_pass(self):
        def unavailable():
            raise qualify.QualificationPreconditionError("Git is unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            code, summary = qualify.run_qualification(
                "fast", Path(temporary) / "result",
                command_runner=self._success, git_provenance=unavailable,
            )
        self.assertEqual(2, code)
        self.assertEqual("BLOCKED", summary["verdict"])
        self.assertEqual("unavailable", summary["git_sha"])

    def test_successful_test_process_without_metadata_is_failure(self):
        def missing_metadata(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, stdout="ok\n")

        with tempfile.TemporaryDirectory() as temporary:
            code, summary = qualify.run_qualification(
                "fast", Path(temporary) / "result",
                command_runner=missing_metadata,
                git_provenance=lambda: self.PROVENANCE,
            )
        self.assertEqual(1, code)
        self.assertEqual("FAIL", summary["verdict"])
        self.assertIn("metadata is missing", summary["phases"][0]["reason"])

    def test_successful_build_process_without_artifact_is_failure(self):
        def missing_artifact(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, stdout="ok\n")

        with tempfile.TemporaryDirectory() as temporary:
            code, summary = qualify.run_qualification(
                "build", Path(temporary) / "result",
                command_runner=missing_artifact,
                git_provenance=lambda: self.PROVENANCE,
            )
        self.assertEqual(1, code)
        self.assertEqual("FAIL", summary["verdict"])
        self.assertIn("artifact is missing", summary["phases"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
