import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from webcheck.http_client import check_url # type: ignore

class TestCheckUrl(unittest.TestCase):
    @patch("webcheck.http_client.urlopen")
    def test_successful_response(self, mock_urlopen):
        response = MagicMock()
        response.status = 200
        response.headers.items.return_value = [
            ("Content-Type", "text/html")
        ]
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        result = check_url("https://example.com")

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["headers"]["Content-Type"], "text/html")
        self.assertIsNone(result["error"])

    @patch("webcheck.http_client.urlopen")
    def test_http_error_response(self, mock_urlopen):
        error = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(
            "https://example.com/missing",
            404,
            "Not Found",
            {},
            None,
        )
        mock_urlopen.side_effect = error

        result = check_url("https://example.com/missing")

        self.assertEqual(result["status_code"], 404)
        self.assertIsNone(result["error"])

    @patch("webcheck.http_client.urlopen")
    def test_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        result = check_url("http://127.0.0.1:1", timeout=2)

        self.assertIsNone(result["status_code"])
        self.assertIn("Connection refused", result["error"])


if __name__ == "__main__":
    unittest.main
