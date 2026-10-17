from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """Return whether *url* is a well-formed HTTP or HTTPS URL.

    This performs basic input checks needed before the URL is passed to the
    HTTP client: the value must be a non-empty string, use HTTP or HTTPS, have
    a hostname, contain no whitespace, and have a valid optional port.

    This is a syntax check only. It does not contact the host, verify that DNS
    resolves, or check whether the resolved address is public; those checks
    belong to the HTTP client. Malformed authority details raised by
    ``urlparse`` (such as invalid ports or IPv6 syntax) are treated as invalid.

    Returns:
        ``True`` if the basic checks pass; otherwise ``False``.
    """
    # Guard the type explicitly because callers may invoke this outside the CLI.
    if not isinstance(url, str) or not url:
        return False

    try:
        parsed = urlparse(url)

        # Limit this tool to web protocols, and reject relative URLs or URLs
        # without a network host.
        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.hostname:
            return False

        # Do not silently accept spaces in user input; encoded spaces (%20) are
        # allowed because they contain no literal whitespace.
        if any(char.isspace() for char in url):
            return False

        # Reading .port can itself raise ValueError for non-numeric or malformed
        # ports; a supplied numeric port must also be within the TCP/UDP range.
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            return False

        return True
    except ValueError:
        # urlparse's hostname/port properties can raise for malformed URL syntax.
        return False
