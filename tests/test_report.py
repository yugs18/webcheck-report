"""Tests for assembling and persisting website-check reports."""

import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main
