"""Tests for the pinned socket HTTP client.

These tests focus on the behavior that matters for the reachability checker:
connection pinning, correct request construction, and preserving redirect
responses instead of silently following them.
"""

import socket
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from webcheck.http_client import PinnedHTTPConnection, PinnedHTTPSConnection, check_url, connect_to_address  # type: ignore

# A public IPv4 address used as a fixed, known-good socket target across tests.
PUBLIC = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))


class TestPinnedConnection(unittest.TestCase):
    @patch("webcheck.http_client.socket.socket")
    def test_connect_to_address_uses_exact_sockaddr(self, socket_factory):
        """Ensure the TCP socket connects to the exact approved sockaddr tuple."""
        fake_socket = Mock()
        socket_factory.return_value = fake_socket

        result = connect_to_address(PUBLIC, timeout=3.0)

        # The socket factory should receive the exact family/type/protocol tuple
        # from the DNS result; we deliberately avoid any extra resolution step.
        socket_factory.assert_called_once_with(PUBLIC[0], PUBLIC[1], PUBLIC[2])
        fake_socket.settimeout.assert_called_once_with(3.0)
        fake_socket.connect.assert_called_once_with(PUBLIC[4])
        self.assertIs(result, fake_socket)

    @patch("webcheck.http_client.connect_to_address")
    def test_https_wraps_socket_using_original_hostname(self, connect_mock):
        """TLS should validate using the original host name, not the IP literal."""
        raw_socket = Mock()
        tls_socket = Mock()
        connect_mock.return_value = raw_socket
        context = Mock()
        context.wrap_socket.return_value = tls_socket

        connection = PinnedHTTPSConnection(
            "example.test", 443, PUBLIC, timeout=2.0, context=context
        )
        connection.connect()

        # The transport stays pinned to the approved resolved IP while the TLS
        # handshake still uses the actual hostname for SNI and certificate checks.
        connect_mock.assert_called_once_with(PUBLIC, 2.0)
        context.wrap_socket.assert_called_once_with(
            raw_socket, server_hostname="example.test"
        )
        self.assertIs(connection.sock, tls_socket)
        connection.close()


class TestCheckURL(unittest.TestCase):
    @patch("webcheck.http_client.resolve_public_host", return_value=[PUBLIC])
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_request_uses_pinned_connection_and_origin_form_target(
        self, connection_class, resolver
    ):
        """Check that the request is sent with the pinned socket and correct path."""
        connection = connection_class.return_value
        response = SimpleNamespace(
            status=200,
            getheaders=lambda: [("Content-Type", "text/plain")],
            close=Mock(),
        )
        connection.getresponse.return_value = response

        result = check_url("http://example.test/path?q=1")

        # The host must be checked against an approved public address list before
        # the request is attempted.
        resolver.assert_called_once_with("example.test", 80)
        connection_class.assert_called_once_with(
            "example.test", 80, PUBLIC, timeout=10.0
        )
        connection.connect.assert_called_once_with()
        connection.request.assert_called_once_with(
            "GET",
            "/path?q=1",
            headers={
                "User-Agent": "WebCheckReport/0.1",
                "Host": "example.test",
                "Connection": "close",
            },
        )
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["headers"]["Content-Type"], "text/plain")
        self.assertIsNone(result["error"])
        connection.close.assert_called_once_with()

    @patch("webcheck.http_client.resolve_public_host", return_value=[PUBLIC])
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_redirect_is_returned_not_followed(self, connection_class, resolver):
        """Ensure redirects remain visible instead of being silently followed."""
        connection = connection_class.return_value
        response = SimpleNamespace(
            status=302,
            getheaders=lambda: [("Location", "http://other.example/")],
            close=Mock(),
        )
        connection.getresponse.return_value = response

        result = check_url("http://example.test/")

        # A redirect is still a legitimate server response; the check should show
        # it as a 3xx instead of treating it as a normal page fetch.
        self.assertEqual(result["status_code"], 302)
        self.assertEqual(result["headers"]["Location"], "http://other.example/")
        connection.request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
