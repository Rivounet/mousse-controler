from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.qualification import measure_test_architecture as measurement


class TestQualityMeasurementTests(unittest.TestCase):
    def test_every_production_module_has_a_direct_test_owner(self) -> None:
        result = measurement.measure()

        self.assertEqual(result["schema"], "mousse-test-architecture-v1")
        self.assertEqual(result["modules_without_direct_test_reference"], [])
        self.assertEqual(
            result["directly_referenced_modules"], result["production_modules"],
        )
        self.assertEqual(result["short_polling_sleep_calls"], 0)
        self.assertTrue(all(
            count > 0 for count in result["test_cases_by_layer"].values()
        ))

    def test_command_writes_the_measured_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "quality" / "architecture.json"
            code = measurement.main(["--output", str(output)])

            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
