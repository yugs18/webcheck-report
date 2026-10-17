import json
import tempfile
import unittest
from pathlib import Path

from webcheck.report import create_report, save_report # type: ignore

class TestReport(unittest.TestCase):
    def test_create_report_includes_timestamp_and_result(self):
        result = {"url": "https://example.com", "status_code": 200}

        report = create_report(result)

        self.assertIn("generated_at", report)
        self.assertEqual(report["result"], result)

    def test_save_report_writes_valid_json(self):
        report = {
            "generated_at": "2026-10-17T00:00:00+00:00",
            "result": {"url": "https://example.com", "status_code": 200},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.json"
            save_report(report, str(output_path))

            with output_path.open(encoding="utf-8") as file:
                loaded = json.load(file)

            self.assertEqual(loaded, report)


if __name__ == "__main__":
    unittest.main
