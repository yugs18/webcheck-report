"""Tests for the public-IP safety policy used during DNS validation.

These tests verify that non-public DNS records are filtered out, and that the
resolver rejects a result set when no approved public address remains.
"""

import ipaddress
import socket
import threading
import unittest
from unittest.mock import patch

from webcheck.http_client import resolve_public_host, is_approved_public_ip  # type: ignore

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

    def test_dns_resolution_has_a_bounded_caller_wait(self):
        entered = threading.Event()
        release = threading.Event()
        worker_finished = threading.Event()

        def slow_resolver(*args, **kwargs):
            entered.set()
            release.wait(2.0)
            worker_finished.set()
            return [PUBLIC]

        try:
            with patch(
                "webcheck.http_client.socket.getaddrinfo",
                side_effect=slow_resolver,
            ):
                with self.assertRaisesRegex(TimeoutError, "DNS resolution timed out"):
                    resolve_public_host("slow.example.test", 443, timeout=0.05)
            self.assertTrue(entered.wait(0.5), "Resolver worker did not start")
        finally:
            # Release the daemon resolver worker so it cannot affect later tests.
            release.set()

        self.assertTrue(worker_finished.wait(0.5), "Resolver worker did not exit")

    def test_mapped_loopback_is_rejected_by_policy(self):
        self.assertFalse(
            is_approved_public_ip("::ffff:127.0.0.1")
        )


    def test_mapped_public_ipv4_uses_embedded_ipv4_policy(self):
        self.assertEqual(
            is_approved_public_ip("::ffff:8.8.8.8"),
            is_approved_public_ip("8.8.8.8"),
        )

    def test_multicast_and_scoped_global_addresses_are_rejected(self):
        for value in (
            "224.0.0.1",             # IPv4 multicast can still be is_global
            "ff02::1",               # IPv6 multicast
            "2001:4860::8888%eth0",  # scoped global IPv6 literal
            "::ffff:224.0.0.1",      # IPv4-mapped multicast
        ):
            with self.subTest(address=value):
                self.assertFalse(is_approved_public_ip(value))

        # A non-zero sockaddr scope ID must also be rejected, even if the
        # printable address has no percent/zone suffix and is otherwise global.
        scoped_sockaddr = (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("2001:4860:4860::8888", 443, 0, 7),
        )
        with patch(
            "webcheck.http_client.socket.getaddrinfo",
            return_value=[scoped_sockaddr],
        ):
            with self.assertRaises(ValueError):
                resolve_public_host("example.test", 443)

class TestIPAddressEdgeCases(unittest.TestCase):
    def test_non_global_addresses_are_not_global(self):
        addresses = [
            # IPv4 loopback and private ranges
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",

            # IPv4 link-local and reserved
            "169.254.1.1",
            "240.0.0.1",

            # IPv6 loopback, unique-local and link-local
            "::1",
            "fc00::1",
            "fe80::1",

            # Documentation-only IPv6 range
            "2001:db8::1",

            # IPv4-mapped IPv6 loopback
            "::ffff:127.0.0.1",

            # Scoped IPv6 link-local address
            "fe80::1%eth0",
        ]

        for value in addresses:
            with self.subTest(address=value):
                address = ipaddress.ip_address(value)
                self.assertFalse(
                    address.is_global,
                    f"{value} unexpectedly classified as global",
                )

    def make_dns_result(self, value, port=443):
        address = ipaddress.ip_address(value)

        if address.version == 4:
            family = socket.AF_INET
            sockaddr = (value, port)
        else:
            family = socket.AF_INET6

            # Preserve the IPv6 scope identifier when present.
            scope_id = 0
            if "%" in value:
                value, scope = value.split("%", 1)
                scope_id = socket.if_nametoindex(scope) if scope else 0

            sockaddr = (value, port, 0, scope_id)

        return (
            family,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            sockaddr,
        )

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_dns_filter_rejects_non_global_edge_cases(self, getaddrinfo):
        addresses = [
            "127.0.0.1",
            "10.0.0.1",
            "169.254.1.1",
            "240.0.0.1",
            "::1",
            "fc00::1",
            "fe80::1",
            "2001:db8::1",
            "::ffff:127.0.0.1",
        ]

        for value in addresses:
            with self.subTest(address=value):
                getaddrinfo.return_value = [
                    self.make_dns_result(value)
                ]

                with self.assertRaises(ValueError):
                    resolve_public_host("example.test", 443)

    @patch("webcheck.http_client.socket.getaddrinfo")
    def test_mixed_dns_answers_keep_only_global_candidates(self, getaddrinfo):
        unsafe = self.make_dns_result("127.0.0.1")
        public_v4 = self.make_dns_result("8.8.8.8")
        public_v6 = self.make_dns_result("2001:4860:4860::8888")

        getaddrinfo.return_value = [
            unsafe,
            public_v4,
            public_v6,
        ]

        result = resolve_public_host("example.test", 443)

        self.assertEqual(
            {item[4][0] for item in result},
            {"8.8.8.8", "2001:4860:4860::8888"},
        )

    def test_ipv4_mapped_loopback_is_rejected(self):
        mapped_loopback = ipaddress.ip_address("::ffff:127.0.0.1")

        self.assertFalse(mapped_loopback.is_global)

    def test_ipv4_mapped_public_address_classification(self):
        mapped_public = ipaddress.ip_address("::ffff:8.8.8.8")
        ipv4_address = ipaddress.ip_address("8.8.8.8")

        self.assertEqual(
            mapped_public.is_global,
            ipv4_address.is_global,
        )

    def test_scoped_ipv6_link_local_is_not_global(self):
        address = ipaddress.ip_address("fe80::1%eth0")

        self.assertFalse(address.is_global)
        self.assertTrue(address.is_link_local)


    def test_scoped_ipv6_loopback_is_not_global(self):
        address = ipaddress.ip_address("::1%lo")

        self.assertFalse(address.is_global)
        self.assertTrue(address.is_loopback)


if __name__ == "__main__":
    unittest.main()
