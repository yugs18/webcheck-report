"""Tests for basic HTTP and HTTPS URL syntax validation."""

import unittest

from webcheck.url_validator import validate_url # type: ignore

class TestValidateUrl(unittest.TestCase):
    """Cover accepted URL forms and inputs that should be rejected."""

    def test_accepts_https_url(self):
        """HTTPS URLs with a hostname are valid input."""
        self.assertTrue(validate_url("https://example.com"))

    def test_accepts_http_url_with_path(self):
        """A path after a valid HTTP authority does not invalidate the URL."""
        self.assertTrue(validate_url("http://example.com/path"))

    def test_rejects_unsupported_scheme(self):
        """Non-web schemes such as FTP are outside this checker's scope."""
        self.assertFalse(validate_url("ftp://example.com"))

    def test_rejects_missing_scheme(self):
        """A bare hostname is not a complete HTTP(S) URL."""
        self.assertFalse(validate_url("example.com"))

    def test_rejects_missing_hostname(self):
        """A scheme and path without a hostname must be rejected."""
        self.assertFalse(validate_url("https:///misssing-host"))

    def test_structurally_valid_loopback_url(self):
        """Syntax validation allows loopback; the network-safety check blocks it."""
        self.assertTrue(validate_url("https://127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
