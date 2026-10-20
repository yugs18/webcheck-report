"""End-to-end tests for the ``python -m webcheck`` command."""

import json, subprocess, sys, tempfile, unittest
import threading
from pathlib import Path
from unittest.mock import patch

from webcheck.__main__ import _run_check_with_wall_clock_limit  # type: ignore

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


if __name__ == "__main__":
    unittest.main()
