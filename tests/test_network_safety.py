"""Tests for the public-IP safety policy used during DNS validation.

These tests verify that non-public DNS records are filtered out, and that the
resolver rejects a result set when no approved public address remains.
"""

import socket
import unittest
from unittest.mock import patch

from webcheck.http_client import resolve_public_host  # type: ignore

# A known public IPv4 address used to simulate a valid global destination.
PUBLIC = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))
# A local loopback address used to simulate a prohibited private destination.
LOOPBACK = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))


class TestAddressFiltering(unittest.TestCase):
    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_filters_loopback_from_mixed_answers(self, mock_dns):
        """Mixed DNS answers should be reduced to public addresses only."""
        mock_dns.return_value = [PUBLIC, LOOPBACK]
        self.assertEqual(resolve_public_host("example.test", 443), [PUBLIC])

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_all_prohibited_raises(self, mock_dns):
        """If every resolved address is non-public, the host must be rejected."""
        mock_dns.return_value = [LOOPBACK]
        with self.assertRaises(ValueError):
            resolve_public_host("example.test", 443)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_empty_results_raise(self, mock_dns):
        """An empty DNS answer means no usable destination was found."""
        mock_dns.return_value = []
        with self.assertRaises(OSError):
            resolve_public_host("example.test", 443)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_dns_error_propagates(self, mock_dns):
        """Underlying DNS failures should remain visible to the caller."""
        mock_dns.side_effect = socket.gaierror("DNS failed")
        with self.assertRaises(socket.gaierror):
            resolve_public_host("example.test", 443)


if __name__ == "__main__":
    unittest.main()
