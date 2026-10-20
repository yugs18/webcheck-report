import ipaddress
import unittest

from webcheck.http_client import normalize_hostname #type: ignore


class TestHostnamePolicy(unittest.TestCase):
    def test_ascii_hostname_is_lowercased(self):
        self.assertEqual(
            normalize_hostname("Example.COM"),
            "example.com",
        )

    def test_unicode_hostname_becomes_ascii_idna(self):
        self.assertEqual(
            normalize_hostname("bücher.example"),
            "xn--bcher-kva.example",
        )

    def test_trailing_dot_is_preserved(self):
        self.assertEqual(
            normalize_hostname("example.com."),
            "example.com.",
        )

    def test_invalid_idna_hostname_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_hostname("bad host.example")

    def test_ip_literals_are_not_misclassified_as_idn(self):
        self.assertEqual(
            normalize_hostname("127.0.0.1"),
            "127.0.0.1",
        )
        self.assertEqual(
            normalize_hostname("2001:db8::1"),
            "2001:db8::1",
        )


if __name__ == "__main__":
    unittest.main()