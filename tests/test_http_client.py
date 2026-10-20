"""Tests for the pinned socket HTTP client.

These tests focus on the behavior that matters for the reachability checker:
connection pinning, correct request construction, and preserving redirect
responses instead of silently following them.
"""

import ssl
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from webcheck.http_client import PinnedHTTPConnection, PinnedHTTPSConnection, check_url, connect_to_address, _remaining_timeout #type: ignore

# A public IPv4 address used as a fixed, known-good socket target across tests.
PUBLIC_HTTP = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))
SECOND_PUBLIC_HTTP = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("1.1.1.1", 80))
class TestPinnedConnection(unittest.TestCase):
    @patch("webcheck.http_client.socket.socket")
    def test_connect_to_address_uses_exact_sockaddr(self, socket_factory):
        """Ensure the TCP socket connects to the exact approved sockaddr tuple."""
        fake_socket = Mock()
        socket_factory.return_value = fake_socket

        result = connect_to_address(PUBLIC_HTTP, timeout=3.0)

        # The socket factory should receive the exact family/type/protocol tuple
        # from the DNS result; we deliberately avoid any extra resolution step.
        socket_factory.assert_called_once_with(PUBLIC_HTTP[0], PUBLIC_HTTP[1], PUBLIC_HTTP[2])
        fake_socket.settimeout.assert_called_once_with(3.0)
        fake_socket.connect.assert_called_once_with(PUBLIC_HTTP[4])
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
            "example.test", 443, PUBLIC_HTTP, timeout=2.0, context=context
        )
        connection.connect()

        # The transport stays pinned to the approved resolved IP while the TLS
        # handshake still uses the actual hostname for SNI and certificate checks.
        connect_mock.assert_called_once_with(PUBLIC_HTTP, 2.0)
        context.wrap_socket.assert_called_once_with(
            raw_socket, server_hostname="example.test"
        )
        self.assertIs(connection.sock, tls_socket)
        connection.close()

    @patch("webcheck.http_client.socket.socket")
    def test_socket_closes_when_tcp_convert_fails(self, socket_factory):
        fake_socket = Mock()
        fake_socket.connect.side_effect = OSError("Connection failed")
        socket_factory.return_value = fake_socket

        with self.assertRaises(OSError):
            connect_to_address(PUBLIC_HTTP, timeout=1.0)

        fake_socket.settimeout.assert_called_once_with(1.0)
        fake_socket.connect.assert_called_once_with(PUBLIC_HTTP[4])
        fake_socket.close.assert_called_once_with()

    @patch("webcheck.http_client.connect_to_address")
    def test_raw_socket_closes_when_tls_wrapping_fails(
        self, connect_mock
    ):
        raw_socket = Mock()
        connect_mock.return_value = raw_socket

        context = Mock()
        context.wrap_socket.side_effect = ssl.SSLError(
            "Simulated TLS failure"
        )

        connection = PinnedHTTPSConnection(
            "example.test",
            443,
            PUBLIC_HTTP,
            timeout=2.0,
            context=context,
        )

        with self.assertRaises(ssl.SSLError):
            connection.connect()

        raw_socket.close.assert_called_once_with()
        self.assertIsNone(connection.sock)


class TestCheckURL(unittest.TestCase):
    @patch("webcheck.http_client.resolve_public_host", return_value=[PUBLIC_HTTP])
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
        resolver.assert_called_once()
        resolver_args, resolver_kwargs = resolver.call_args
        self.assertEqual(resolver_args, ("example.test", 80))
        self.assertGreater(resolver_kwargs["timeout"], 0)
        self.assertLessEqual(resolver_kwargs["timeout"], 10.0)
        connection_class.assert_called_once()

        args, kwargs = connection_class.call_args

        self.assertEqual(args[0], "example.test")
        self.assertEqual(args[1], 80)
        self.assertEqual(args[2], PUBLIC_HTTP)

        self.assertGreater(kwargs["timeout"], 0)
        self.assertLessEqual(kwargs["timeout"], 10.0)

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

    @patch("webcheck.http_client.resolve_public_host", return_value=[PUBLIC_HTTP])
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_redirect_is_reported_but_not_followed(
        self, connection_class, resolver
    ):
        """Check that the request is sent with the pinned socket and correct path."""
        connection = connection_class.return_value
        response = SimpleNamespace(
            status=302,
            getheaders=lambda: [("Location", "http://127.0.0.1/admin")],
            close=Mock(),
        )
        connection.getresponse.return_value = response

        result = check_url("http://example.test/")

        # The host must be checked against an approved public address list before
        # the request is attempted.
        resolver.assert_called_once()
        resolver_args, resolver_kwargs = resolver.call_args
        self.assertEqual(resolver_args, ("example.test", 80))
        self.assertGreater(resolver_kwargs["timeout"], 0)
        self.assertLessEqual(resolver_kwargs["timeout"], 10.0)
        connection_class.assert_called_once()

        args, kwargs = connection_class.call_args

        self.assertEqual(args[0], "example.test")
        self.assertEqual(args[1], 80)
        self.assertEqual(args[2], PUBLIC_HTTP)

        self.assertGreater(kwargs["timeout"], 0)
        self.assertLessEqual(kwargs["timeout"], 10.0)

        connection.connect.assert_called_once_with()
        connection.request.assert_called_once_with(
            "GET",
            "/",
            headers={
                "User-Agent": "WebCheckReport/0.1",
                "Host": "example.test",
                "Connection": "close",
            },
        )
        self.assertEqual(result["status_code"], 302)
        self.assertEqual(result["headers"]["Location"], "http://127.0.0.1/admin")
        self.assertIsNone(result["error"])
        connection.close.assert_called_once_with()

    @patch("webcheck.http_client.resolve_public_host", return_value=[PUBLIC_HTTP])
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


    @patch("webcheck.http_client.resolve_public_host")
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_retries_next_cantidate_after_connection_failure(self, connection_class, resolver):
        resolver.return_value = [PUBLIC_HTTP, SECOND_PUBLIC_HTTP]

        first_connection = Mock()
        first_connection.connect.side_effect = OSError("Connection failed")

        second_connection = Mock()

        response = Mock()
        response.status = 200
        response.getheaders.return_value = [("Content-Type", "text/plain"),]
        response.close = Mock()

        second_connection.getresponse.return_value = response

        connection_class.side_effect = [first_connection, second_connection]

        result = check_url("http://example.test/")

        self.assertEqual(result["status_code"], 200)
        self.assertIsNone(result["error"])

        self.assertEqual(connection_class.call_count, 2)
        first_connection.close.assert_called_once_with()
        second_connection.connect.assert_called_once_with()
        second_connection.close.assert_called_once_with()

    @patch("webcheck.http_client.resolve_public_host")
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_unicode_hostname_uses_idna_for_dns_and_host_header(self, connection_class, resolver):
        resolver.return_value = [PUBLIC_HTTP]

        response = Mock()
        response.status = 200
        response.getheaders.return_value = [
            ("Content-Type", "text/plain"),
        ]
        response.close = Mock()

        connection = Mock()
        connection.getresponse.return_value = response
        connection_class.return_value = connection

        result = check_url("http://bücher.example/path?q=1")

        self.assertEqual(result["status_code"], 200)
        resolver.assert_called_once()
        resolver_args, resolver_kwargs = resolver.call_args
        self.assertEqual(resolver_args, ("xn--bcher-kva.example", 80))
        self.assertGreater(resolver_kwargs["timeout"], 0)
        self.assertLessEqual(resolver_kwargs["timeout"], 10.0)

        request_args, request_kwargs = connection.request.call_args
        self.assertEqual(request_args[0], "GET")
        self.assertEqual(request_args[1], "/path?q=1")
        self.assertEqual(
            request_kwargs["headers"]["Host"],
            "xn--bcher-kva.example",
        )

    @patch("webcheck.http_client.resolve_public_host")
    def test_check_url_rejects_invalid_timeout_values(self, resolver):
        for invalid_timeout in (
            0,
            -1,
            float("nan"),
            float("inf"),
            -float("inf"),
            True,
            "10",
            301,
            10**1000,
        ):
            with self.subTest(timeout=invalid_timeout):
                result = check_url("http://example.test", timeout=invalid_timeout)
                self.assertIsNone(result["status_code"])
                self.assertIn("finite positive", result["error"])
        resolver.assert_not_called()

    @patch("webcheck.http_client.time.monotonic")
    @patch("webcheck.http_client.resolve_public_host")
    @patch("webcheck.http_client.PinnedHTTPConnection")
    def test_deadline_prevents_retry_after_budget_expires(
        self, connection_class, resolver, monotonic
    ):
        resolver.return_value = [PUBLIC_HTTP, SECOND_PUBLIC_HTTP]

        # Deadline starts at 110. First attempt begins at 100.
        # The next attempt would begin after the budget has expired.
        monotonic.side_effect = [100.0, 100.0, 100.0, 111.0]

        first_connection = Mock()
        first_connection.connect.side_effect = OSError(
            "Connection failed"
        )
        connection_class.return_value = first_connection

        result = check_url("http://example.test/", timeout=10.0)

        self.assertIsNone(result["status_code"])
        self.assertIn("deadline exceeded", result["error"].lower())
        self.assertEqual(connection_class.call_count, 1)
        first_connection.close.assert_called_once_with()

    def test_response_after_deadline(self):
        clock = [100.0]

        with patch(
            "webcheck.http_client.socket.getaddrinfo",
            return_value=[PUBLIC_HTTP],
        ):
            with patch(
                "webcheck.http_client.PinnedHTTPConnection"
            ) as connection_class:

                connection = connection_class.return_value
                response = connection.getresponse.return_value

                response.status = 200
                response.getheaders.return_value = []

                def fake_monotonic():
                    return clock[0]

                def return_late_response():
                    clock[0] = 111.0  # Deadline is 110.0
                    return response

                connection.getresponse.side_effect = return_late_response

                with patch(
                    "webcheck.http_client.time.monotonic",
                    side_effect=fake_monotonic,
                ):
                    result = check_url("http://example.test")

        self.assertIsNone(result["status_code"])
        self.assertIn(
            "Operation deadline exceeded",
            result["error"],
        )
        connection.close.assert_called_once()
        response.close.assert_called_once()

    def test_remaining_timeout_decreases(self):
        with patch(
            "webcheck.http_client.time.monotonic",
            return_value=103.0,
        ):
            self.assertEqual(_remaining_timeout(110.0), 7.0)


    def test_remaining_timeout_rejects_exhausted_deadline(self):
        with patch(
            "webcheck.http_client.time.monotonic",
            return_value=110.0,
        ):
            with self.assertRaisesRegex(
                TimeoutError, "Operation deadline exceeded"
            ):
                _remaining_timeout(110.0)


if __name__ == "__main__":
    unittest.main()
