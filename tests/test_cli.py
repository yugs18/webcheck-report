"""End-to-end tests for the ``python -m webcheck`` command."""

import json, subprocess, sys, tempfile, unittest
from pathlib import Path

class TestCLI(unittest.TestCase):
    """Exercise CLI argument handling, exit codes, and report creation."""

    def test_invalid_url_returns_exit_code_2(self):
        """A URL without an HTTP(S) scheme fails before a report is written."""
        result = subprocess.run(
            [sys.executable, "-m", "webcheck", "example.com"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid HTTP/HTTPS URL", result.stderr)

    def test_connection_error_saves_report(self):
        """A failed check still saves its result and exits with code 1."""
        # Use a temporary output path and a loopback destination that the
        # network-safety check rejects, avoiding dependence on external servers.
        with tempfile.TemporaryDirectory()as temp_dir:
            output_path = Path(temp_dir) / "report.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "webcheck",
                    "http://127.0.0.1:1",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            self.assertEqual(result.returncode, 1)
            self.assertTrue(output_path.exists())

            # The CLI should preserve the failure details in the JSON report,
            # not only print an error to the terminal.
            with output_path.open(encoding="utf-8") as file:
                report = json.load(file)

            self.assertIsNone(report["result"]["status_code"])
            self.assertIsNotNone(report["result"]["error"])


if __name__ == "__main__":
    unittest.main()
