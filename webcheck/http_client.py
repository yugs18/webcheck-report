# http_client.py

import time, ipaddress, socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from webcheck.url_validator import validate_url # type: ignore


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resolve_public_host(host: str, port:int) -> None:
    addresses = socket.getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
    )

    if not addresses:
        raise OSError("Hostname did not resolve to an IP address")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("Destination resolves to a non-public IP address")


def check_url(url: str, timeout: float = 10.0) -> dict:
    """Request a public HTTP(S) URL without automatically following redirects."""
    start_time = time.perf_counter()

    if not validate_url(url):
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": 0.0,
            "error": "Invalid HTTP/HTTPS URL",
        }

    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        if parsed.hostname is None:
            raise ValueError("Invalid HTTP/HTTPS URL")
        resolve_public_host(parsed.hostname, port)
    except (OSError, ValueError) as error:
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(
                time.perf_counter() - start_time, 4
            ),
            "error": str(error),
        }

    request = Request(
        url,
        headers={"User-Agent": "WebCheckReport/0.1"},
        method="GET",
    )

    opener = build_opener(NoRedirectHandler())

    try:
        with opener.open(request, timeout=timeout) as response:
            return {
                "url": url,
                "status_code": response.status,
                "headers": dict(response.headers.items()),
                "elapsed_seconds": round(
                    time.perf_counter() - start_time, 4
                ),
                "error": None,
            }

    except HTTPError as error:
        # Includes redirects such as 301 and 302; they are not followed.
        return {
            "url": url,
            "status_code": error.code,
            "headers": dict(error.headers.items()) if error.headers is not None else {},
            "elapsed_seconds": round(
                time.perf_counter() - start_time, 4
            ),
            "error": None,
        }

    except (URLError, TimeoutError, OSError) as error:
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(
                time.perf_counter() - start_time, 4
            ),
            "error": str(error),
        }