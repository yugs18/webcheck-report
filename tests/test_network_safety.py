
import unittest
from unittest.mock import patch

from webcheck.http_client import resolve_public_host # type: ignore


class TestNetworkSafety(unittest.TestCase):
    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_rejects_loopback_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 80))
        ]

        with self.assertRaisesRegex(ValueError, "non-public"):
            resolve_public_host("localhost", 80)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_rejects_private_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.10", 80))
        ]

        with self.assertRaisesRegex(ValueError, "non-public"):
            resolve_public_host("internal.example", 80)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_rejects_loopback_ipv6(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (10, 1, 6, "", ("::1", 80, 0, 0))
        ]

        with self.assertRaisesRegex(ValueError, "non-public"):
            resolve_public_host("localhost", 80)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_accepts_public_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443))
        ]

        resolve_public_host("example.com", 443)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_rejects_mixed_public_and_private_addresses(
        self, mock_getaddrinfo
    ):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("10.0.0.5", 443)),
        ]

        with self.assertRaisesRegex(ValueError, "non-public"):
            resolve_public_host("mixed.example", 443)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_rejects_empty_dns_result(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = []

        with self.assertRaisesRegex(OSError, "did not resolve"):
            resolve_public_host("missing.example", 80)


if __name__ == "__main__":
    unittest.main()
