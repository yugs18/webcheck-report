
import unittest
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from webcheck.http_client import check_url # type: ignore


class TestCheckURL(unittest.TestCase):
    @patch("webcheck.http_client.build_opener")
    @patch("webcheck.http_client.resolve_public_host")
    def test_successful_response(
        self, mock_resolve, mock_build_opener
    ):
        response = MagicMock()
        response.status = 200
        response.headers.items.return_value = [
            ("Content-Type", "text/html")
        ]
        response.__enter__.return_value = response

        opener = MagicMock()
        opener.open.return_value = response
        mock_build_opener.return_value = opener

        result = check_url("https://example.com")

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(
            result["headers"]["Content-Type"], "text/html"
        )
        self.assertIsNone(result["error"])
        mock_resolve.assert_called_once_with("example.com", 443)
        opener.open.assert_called_once()

    @patch("webcheck.http_client.build_opener")
    @patch("webcheck.http_client.resolve_public_host")
    def test_http_error_response(
        self, mock_resolve, mock_build_opener
    ):
        error = HTTPError(
            "https://example.com/missing",
            404,
            "Not Found",
            Message(),
            None,
        )

        opener = MagicMock()
        opener.open.side_effect = error
        mock_build_opener.return_value = opener

        result = check_url("https://example.com/missing")

        self.assertEqual(result["status_code"], 404)
        self.assertIsNone(result["error"])

    @patch("webcheck.http_client.build_opener")
    @patch("webcheck.http_client.resolve_public_host")
    def test_connection_error(
        self, mock_resolve, mock_build_opener
    ):
        opener = MagicMock()
        opener.open.side_effect = URLError("Connection refused")
        mock_build_opener.return_value = opener

        result = check_url("https://example.com", timeout=2)

        self.assertIsNone(result["status_code"])
        self.assertIn("Connection refused", result["error"])

    @patch("webcheck.http_client.resolve_public_host")
    def test_rejects_non_public_destination(self, mock_resolve):
        mock_resolve.side_effect = ValueError(
            "Destination resolves to a non-public IP address"
        )

        result = check_url("http://127.0.0.1:8080")

        self.assertIsNone(result["status_code"])
        self.assertIn("non-public", result["error"])
        mock_resolve.assert_called_once_with("127.0.0.1", 8080)

    @patch("webcheck.http_client.build_opener")
    @patch("webcheck.http_client.resolve_public_host")
    def test_redirect_is_reported_not_followed(
        self, mock_resolve, mock_build_opener
    ):

        headers = Message()
        headers["Location"] = "http://127.0.0.1/admin"

        redirect = HTTPError(
            "https://example.com",
            302,
            "Found",
            headers,
            None,
        )

        opener = MagicMock()
        opener.open.side_effect = redirect
        mock_build_opener.return_value = opener

        result = check_url("https://example.com")

        self.assertEqual(result["status_code"], 302)
        self.assertEqual(
            result["headers"]["Location"],
            "http://127.0.0.1/admin",
        )
        opener.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
