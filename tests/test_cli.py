"""End-to-end tests for the ``python -m webcheck`` command."""

import json
import subprocess
import sys
import tempfile
import unittest
import threading

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from webcheck.__main__ import _run_check_with_wall_clock_limit, main # type: ignore

class TestCLI(unittest.TestCase):
    """Exercise CLI argument handling, exit codes, and report creation."""

    def test_cli_supervisor_returns_when_check_exceeds_wall_clock_limit(self):
        started = threading.Event()
        release = threading.Event()

        def slow_check(url, timeout):
            started.set()
            release.wait(1.0)
            return {
                "url": url,
                "status_code": 200,
                "headers": {},
                "elapsed_seconds": 1.0,
                "error": None,
            }

        try:
            with patch("webcheck.__main__.check_url", side_effect=slow_check):
                result = _run_check_with_wall_clock_limit(
                    "http://example.test", timeout=0.03
                )

            self.assertTrue(started.wait(0.5), "Check worker did not start")
            self.assertIsNone(result["status_code"])
            self.assertIn("wall-clock limit exceeded", result["error"])
            self.assertGreaterEqual(result["elapsed_seconds"], 0.02)
        finally:
            release.set()

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
                timeout=15,
            )

            self.assertEqual(result.returncode, 1)
            self.assertTrue(output_path.exists())

            # The CLI should preserve the failure details in the JSON report,
            # not only print an error to the terminal.
            with output_path.open(encoding="utf-8") as file:
                report = json.load(file)

            self.assertIsNone(report["result"]["status_code"])
            self.assertIsNotNone(report["result"]["error"])

    def test_report_write_failure_returns_one_without_success_summary(self):
        result_data = {
            "url": "https://example.com",
            "status_code": 200,
            "headers": {},
            "elapsed_seconds": 0.01,
            "error": None,
        }

        stdout = StringIO()
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            # A regular file cannot serve as the parent directory.
            blocker = Path(temp_dir) / "not-a-directory"
            blocker.write_text("blocking file", encoding="utf-8")
            output_path = blocker / "report.json"

            with (
                patch(
                    "webcheck.__main__._run_check_with_wall_clock_limit",
                    return_value=result_data,
                ),
                patch(
                    "sys.argv",
                    [
                        "webcheck",
                        "https://example.com",
                        "--output",
                        str(output_path),
                    ],
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Error saving report", stderr.getvalue())
        self.assertNotIn("Report saved to:", stdout.getvalue())
        self.assertNotIn("HTTP status:", stdout.getvalue())

    def test_serialization_failure_returns_one_without_partial_report(self):
        result_data = {
            "url": "https://example.com",
            "status_code": 200,
            "headers": {},
            "elapsed_seconds": 0.01,
            "error": None,
            "unexpected_value": object(),
        }

        stdout = StringIO()
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "report.json"

            with (
                patch(
                    "webcheck.__main__._run_check_with_wall_clock_limit",
                    return_value=result_data,
                ),
                patch(
                    "sys.argv",
                    [
                        "webcheck",
                        "https://example.com",
                        "--output",
                        str(output_path),
                    ],
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main()

            self.assertFalse(output_path.exists())
            self.assertFalse(output_path.parent.exists())

        self.assertEqual(exit_code, 1)
        self.assertIn("Error saving report", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("Report saved to:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
