"""HTTP request handling for checking publicly reachable websites."""

import time, ipaddress, socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from webcheck.url_validator import validate_url # type: ignore


class NoRedirectHandler(HTTPRedirectHandler):
    """Prevent urllib from following redirects automatically.

    A redirect is useful information about the URL being checked, so callers
    receive its status and headers instead of silently checking a different URL.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Returning None tells urllib not to construct a request for the new URL.
        return None


def resolve_public_host(host: str, port:int) -> None:
    """Resolve a host and raise if it has no addresses or any address is non-public.

    The socket records returned by ``getaddrinfo`` may include IPv4 and IPv6
    addresses. Check every resolved address, rather than only the first one, so
    a hostname with a mix of public and private destinations is rejected.

    Raises:
        OSError: DNS resolution fails or returns no usable addresses.
        ValueError: Any resolved address is not globally routable.
    """
    addresses = socket.getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
    )

    if not addresses:
        raise OSError("Hostname did not resolve to an IP address")

    for address in addresses:
        # getaddrinfo's address tuple stores the numeric IP at index 0 of item 4.
        ip = ipaddress.ip_address(address[4][0])

        # Reject the entire hostname if even one result is local or reserved.
        if not ip.is_global:
            raise ValueError("Destination resolves to a non-public IP address")


def check_url(url: str, timeout: float = 10.0) -> dict:
    """Send a GET request and return a consistent summary of the check.

    Processing happens in stages: validate the URL, resolve its host and check
    the resulting IP addresses, then send the HTTP request. The timeout is
    passed to urllib for the network request.

    The returned mapping always contains ``url``, ``status_code``, ``headers``,
    ``elapsed_seconds``, and ``error``. An HTTP response (including a redirect
    or other error status) has a status code and headers with ``error`` set to
    ``None``. A validation, DNS, connection, or timeout failure has no status
    code; its explanation is stored in ``error``. Invalid input is rejected
    with a fixed elapsed time of ``0.0``; later failures include measured time.
    """
    start_time = time.perf_counter()

    if not validate_url(url):
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": 0.0,
            "error": "Invalid HTTP/HTTPS URL",
        }

    # Parse the URL after validation to determine which port DNS should check.
    # Explicit ports take precedence; otherwise use HTTP's or HTTPS's default.
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Treat DNS and address-policy failures as ordinary check results, so the
    # caller can still produce a report with the reason the request was skipped.
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

    # Use GET to request the page and identify this client with a stable
    # User-Agent. The redirect handler above ensures the requested URL is kept.
    request = Request(
        url,
        headers={"User-Agent": "WebCheckReport/0.1"},
        method="GET",
    )

    # Build a dedicated opener with redirect handling configured for this check.
    opener = build_opener(NoRedirectHandler())

    try:
        with opener.open(request, timeout=timeout) as response:
            # Elapsed time includes the DNS pre-check and the HTTP request.
            # Copy headers to a plain dict before the response is closed.
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
        # urllib uses HTTPError for HTTP statuses it treats as exceptional.
        # These still represent a real server response, so preserve its status
        # and headers and leave the transport-error field empty.
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
        # These failures occurred without a usable HTTP response, so there is no
        # status or response header to report; retain the exception message.
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(
                time.perf_counter() - start_time, 4
            ),
            "error": str(error),
        }