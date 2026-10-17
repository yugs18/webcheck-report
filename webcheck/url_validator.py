from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.hostname:
            return False

        if any(char.isspace() for char in url):
            return False

        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            return False

        return True
    except ValueError:
        return False
