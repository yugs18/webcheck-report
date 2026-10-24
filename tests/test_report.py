"""Tests for assembling and persisting website-check reports."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webcheck.report import create_report, save_report # type: ignore

class TestReport(unittest.TestCase):
    """Check report metadata and the JSON file written for a result."""

    def test_create_report_includes_timestamp_and_result(self):
        """The report adds a generation timestamp and retains the input result."""
        result = {"url": "https://example.com", "status_code": 200}

        report = create_report(result)

        # Verify the timestamp is present without depending on the current time.
        self.assertIn("generated_at", report)
        self.assertEqual(report["result"], result)

    def test_save_report_writes_valid_json(self):
        """A saved report can be parsed back into the original data structure."""
        report = {
            "generated_at": "2026-10-17T00:00:00+00:00",
            "result": {"url": "https://example.com", "status_code": 200},
        }

        # Isolate the output in a temporary folder so the test leaves no report
        # files in the repository and can safely use the normal save operation.
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.json"
            save_report(report, str(output_path))

            with output_path.open(encoding="utf-8") as file:
                loaded = json.load(file)

            self.assertEqual(loaded, report)


    def test_non_serializable_report_does_not_create_output(self):
        report = {"invalid_value": object()}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "report.json"

            with self.assertRaises(TypeError):
                save_report(report, str(output_path))

            self.assertFalse(output_path.exists())
            self.assertFalse(output_path.parent.exists())

    def test_failed_replacement_preserves_existing_report(self):
        report = {
            "generated_at": "2026-10-24T00:00:00+00:00",
            "result": {"url": "https://example.com", "status_code": 200},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.json"
            previous_content = '{"previous": true}\n'
            output_path.write_text(previous_content, encoding="utf-8")

            with patch(
                "webcheck.report.os.replace",
                side_effect=OSError("simulated replacement failure"),
            ):
                with self.assertRaisesRegex(
                    OSError, "simulated replacement failure"
                ):
                    save_report(report, str(output_path))

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                previous_content,
            )
            self.assertEqual(
                list(output_path.parent.glob(".report.json.*.tmp")),
                [],
            )

    def test_save_report_propagates_filesystem_errors(self):
        report = {
            "generated_at": "2026-10-24T00:00:00+00:00",
            "result": {"url": "https://example.com", "status_code": 200},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            blocker = Path(temp_dir) / "not-a-directory"
            blocker.write_text("blocking file", encoding="utf-8")
            output_path = blocker / "report.json"

            with self.assertRaises(OSError):
                save_report(report, str(output_path))


if __name__ == "__main__":
    unittest.main()
