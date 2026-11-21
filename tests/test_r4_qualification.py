from __future__ import annotations

import importlib
from dataclasses import asdict
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
                [phase.name for phase in qualify.phases_for("software", output)],
                ["software-tests"],
            )
            self.assertEqual(
                [phase.name for phase in qualify.phases_for("full-local", output)],
                ["software-tests", "python-compilation", "api-reference-check",
                 "powershell-syntax", "position-agent-build"],
            )

    def test_build_profile_only_builds_into_qualification_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            phase = qualify.phases_for("build", output)[-1]
            self.assertEqual(phase.name, "position-agent-build")
            output_argument = Path(phase.command[phase.command.index("-OutputDirectory") + 1])
            self.assertTrue(output_argument.is_relative_to(output))
            self.assertNotIn("Install", phase.command)

    def test_profile_definition_survives_fresh_process_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            before = qualify.phases_for("full-local", output)
            reloaded = importlib.reload(qualify)
            after = reloaded.phases_for("full-local", output)
            self.assertEqual([asdict(phase) for phase in before],
                             [asdict(phase) for phase in after])


class QualificationOutcomeTests(unittest.TestCase):
    @staticmethod
    def _success(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="ok\n")

    def test_missing_required_tool_is_blocked_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            code, summary = qualify.run_qualification(
                "build", output, command_runner=self._success,
                which=lambda tool: None if tool == "pwsh" else tool,
                git_sha=lambda: "a" * 40,
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
                git_sha=lambda: "b" * 40,
            )
            self.assertEqual(code, 1)
            self.assertEqual(summary["verdict"], "FAIL")
            self.assertEqual(summary["git_sha"], "b" * 40)
            self.assertEqual(summary["exclusions"], list(qualify.MATERIAL_EXCLUSIONS))
            self.assertIn("deliberate failure", (output / "software-tests.log").read_text())

    def test_interruption_is_observable_and_temporary_files_are_cleaned(self):
        def interrupt(_command, **kwargs):
            Path(kwargs["env"]["MC_QUALIFICATION_TEMP"], "marker").write_text("temporary")
            raise KeyboardInterrupt

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            code, summary = qualify.run_qualification(
                "software", output, command_runner=interrupt,
                git_sha=lambda: "c" * 40,
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
            return subprocess.CompletedProcess(command, 0, stdout="ok\n")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "deep" / "qualification" / "result"
            code, summary = qualify.run_qualification(
                "software", output, command_runner=capture_environment,
                git_sha=lambda: "d" * 40,
            )
            self.assertEqual(code, 0)
            self.assertEqual(summary["verdict"], "PASS")
            self.assertEqual(observed["pycache"].parent,
                             qualify.ROOT.parent / "t")
            self.assertFalse(observed["pycache"].exists())
            self.assertFalse((output / ".temporary").exists())


if __name__ == "__main__":
    unittest.main()
