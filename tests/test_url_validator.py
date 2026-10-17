import unittest

from webcheck.url_validator import validate_url # type: ignore

class TestValidateUrl(unittest.TestCase):
    def test_accepts_https_url(self):
        self.assertTrue(validate_url("https://example.com"))

    def test_accepts_http_url_with_path(self):
        self.assertTrue(validate_url("http://example.com/path"))

    def test_rejects_unsupported_scheme(self):
        self.assertFalse(validate_url("ftp://example.com"))

    def test_rejects_missing_scheme(self):
        self.assertFalse(validate_url("example.com"))

    def test_rejects_missing_hostname(self):
        self.assertFalse(validate_url("https:///misssing-host"))


if __name__ == "__main__":
    unittest.main()
