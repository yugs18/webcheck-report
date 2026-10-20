"""URL validation helpers for web reachability checks.

This module intentionally performs lightweight syntax validation only. It does
not resolve DNS, check network reachability, or attempt an HTTP request. Those
broader checks belong in the HTTP client so the validation step stays fast and
predictable while the request layer handles live network behavior.
"""

from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Return whether *url* is a well-formed HTTP or HTTPS URL.

    The goal is to reject malformed input before any network activity occurs.
    This function checks the exact primitives needed to safely hand the URL to
    the HTTP client:

    * the value must be a non-empty string,
    * the scheme must be ``http`` or ``https``,
    * the URL must include a hostname,
    * the input must not contain literal whitespace,
    * if a port is supplied, it must be valid and within the TCP/UDP range.

    This is a structural validation step only. It does not confirm the website is
    reachable, that DNS resolves, or that the target host is public; those checks
    are intentionally performed later in the network layer.

    Args:
        url: The URL string to inspect.

    Returns:
        ``True`` when the URL is syntactically acceptable for HTTP/HTTPS checks,
        otherwise ``False``.
    """
    # Guard explicitly against non-string input and empty values. Some callers may
    # pass a value that is not a URL at all, and we prefer a clean rejection over
    # a confusing downstream error.
    if not isinstance(url, str) or not url:
        return False

    try:
        # Parse once and assess the pieces that matter for a web request.
        parsed = urlparse(url)

        # Restrict the supported protocols to the two expected web schemes.
        # Reject other schemes such as ftp, file, or custom URLs before they reach
        # the HTTP stack.
        if parsed.scheme not in ("http", "https"):
            return False

        # A hostname is required for network requests. Relative URLs, bare paths,
        # and incomplete authorities are rejected here.
        if not parsed.hostname:
            return False

        # Literal whitespace is not permitted in a raw URL string. Encoded spaces
        # such as "%20" are acceptable because they do not appear as whitespace in
        # the input itself.
        if any(char.isspace() for char in url):
            return False

        # Parsing the port can raise ValueError for malformed values, and even a
        # present but invalid numeric port must be rejected to avoid passing bad
        # authority data into the HTTP layer.
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            return False

        return True
    except ValueError:
        # ``urlparse`` may raise when it encounters malformed authority syntax,
        # such as an invalid IPv6 literal or a non-numeric port string.
        # Treat those parse failures as invalid URLs.
        return False
