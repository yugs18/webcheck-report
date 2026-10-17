import json, subprocess, sys, tempfile, unittest
from pathlib import Path

class TestCLI(unittest.TestCase):
    def test_invalid_url_returns_exit_code_2(self):
        result = subprocess.run(
            [sys.executable, "-m", "webcheck", "example.com"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid HTTP/HTTPS URL", result.stderr)


    def test_connection_error_saves_report(self):
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

            with output_path.open(encoding="utf-8") as file:
                report = json.load(file)

            self.assertIsNone(report["result"]["status_code"])
            self.assertIsNotNone(report["result"]["error"])


if __name__ == "__main__":
    unittest.main()
