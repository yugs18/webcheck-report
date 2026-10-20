"""HTTP(S) reachability checks that pin each connection to an approved DNS result.

This module deliberately bypasses environment-configured proxies and instead
connects directly to the IP address chosen from a validated DNS response. The
purpose is to ensure the destination is both syntactically valid and publicly
routable before any HTTP request is sent. The implementation records response
status and headers but does not download the body or follow redirects, which
keeps the check focused on availability and policy compliance rather than full
content fetching.
"""

import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlparse

from webcheck.url_validator import validate_url  # type: ignore

# Use a stable identifier for outbound requests so servers can recognize the
# tool if they log incoming traffic. Keeping this constant centralized makes it
# easy to maintain if the project wants a different user-agent in future.
USER_AGENT = "WebCheckReport/0.1"


def resolve_public_host(host: str, port: int):
    """Return only DNS results whose resolved IP addresses are globally routable.

    This is the network-equivalent of a policy gate: a hostname may resolve to a
    mix of public and private addresses, but the checker should reject that host
    entirely if any returned address is non-public. The filtering is done here so
    the caller can safely connect to one of the approved addresses without
    processing a non-public destination.

    Args:
        host: Hostname or literal IP address to resolve.
        port: Port to use when resolving and connecting.

    Returns:
        A list of ``getaddrinfo`` tuples that passed the public-address check.

    Raises:
        OSError: If the host does not resolve to any IPs at all.
        ValueError: If no resolved address is globally routable.
    """
    # ``getaddrinfo`` produces tuples shaped like:
    # (family, type, proto, canonname, sockaddr)
    # The sockaddr for IPv4 is a 2-tuple (ip, port); for IPv6 it is a 4-tuple
    # containing the address and flow info/ scope id.
    addresses = socket.getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    if not addresses:
        raise OSError("Hostname did not resolve to an IP address")

    approved_addresses = []
    for answer in addresses:
        # Read the actual numeric IP from the sockaddr payload and enforce the
        # public-only policy for the final connection target.
        ip_text = answer[4][0]
        ip = ipaddress.ip_address(ip_text)
        if ip.is_global:
            approved_addresses.append(answer)

    if not approved_addresses:
        raise ValueError("No approved global destination addresses")

    return approved_addresses


def connect_to_address(address_info, timeout):
    """Open a TCP socket to one exact address tuple from ``getaddrinfo``.

    This helper intentionally avoids a second DNS lookup and instead uses the
    already-approved address selection from ``resolve_public_host``. That keeps
    the connection pinned to a specific destination and avoids accidentally
    switching to a different network target during the same check.
    """
    family, socktype, proto, _, sockaddr = address_info
    sock = socket.socket(family, socktype, proto)
    try:
        sock.settimeout(timeout)
        sock.connect(sockaddr)
        return sock
    except Exception:
        sock.close()
        raise


class PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection whose TCP socket is pinned to one approved DNS result."""

    def __init__(self, host, port, address_info, timeout=10.0):
        # Keep the exact resolved socket tuple for this connection so the parent
        # HTTPConnection implementation can be used without re-resolving the host.
        self._address_info = address_info
        super().__init__(host, port, timeout=timeout)

    def connect(self):
        # Replace the default network connection logic with a socket created from
        # the already-approved address tuple.
        self.sock = connect_to_address(self._address_info, self.timeout)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a resolved IP while validating the certificate."""

    def __init__(self, host, port, address_info, timeout=10.0, context=None):
        # Store the selected socket address and the TLS context before the base
        # class initializes its own connection state.
        self._address_info = address_info
        self._tls_context = context or ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=self._tls_context)

    def connect(self):
        # Connect the raw TCP socket first to the approved IP address, then wrap
        # it in TLS. This ensures the certificate validation still uses the real
        # hostname while the transport path remains pinned to the approved IP.
        raw_socket = connect_to_address(self._address_info, self.timeout)
        try:
            self.sock = self._tls_context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except Exception:
            raw_socket.close()
            self.sock = None
            raise


def _failure(url, started, error):
    """Normalize a failed check into the standard result dictionary shape."""
    return {
        "url": url,
        "status_code": None,
        "headers": {},
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "error": str(error),
    }


def _host_authority(host, port, explicit_port):
    """Build the Host header value for the target URL, including IPv6 brackets."""
    # HTTP/1.1 Host headers for IPv6 literals require square brackets, but regular
    # names and IPv4 addresses do not. This helper keeps the header consistent
    # with the authority form used in the URL.
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"{display_host}:{port}" if explicit_port is not None else display_host


def check_url(url: str, timeout: float = 10.0) -> dict:
    """Send a GET request to a URL while pinning the socket to an approved address.

    The function intentionally rejects redirects by returning the redirecting
    response as a status code instead of following it. The checker also records
    only the response metadata needed for a reachability report, not the message
    body itself.

    Args:
        url: Candidate URL to validate and request.
        timeout: Maximum seconds to allow for connection and HTTP exchange.

    Returns:
        A dictionary with the URL, optional status code, response headers, timing,
        and any error text. A successful request returns a numeric status code;
        failures return ``None`` for the status and a human-readable error.
    """
    started = time.perf_counter()

    # Validate the input string before performing any DNS or socket operations.
    # This immediately rejects malformed or unsupported URL values.
    if not validate_url(url):
        return _failure(url, started, "Invalid HTTP/HTTPS URL")

    try:
        parsed = urlparse(url)
        host = parsed.hostname
        explicit_port = parsed.port
    except ValueError as error:
        return _failure(url, started, error)

    if not host:
        return _failure(url, started, "Invalid HTTP/HTTPS URL: missing hostname")
    if parsed.username is not None or parsed.password is not None:
        return _failure(url, started, "Credentials embedded in URLs are not supported")
    if explicit_port == 0:
        return _failure(url, started, "Port 0 is not a valid HTTP destination")

    # Select the effective destination port from the URL, defaulting to the
    # standard port for the scheme when the user did not specify one.
    scheme = parsed.scheme.lower()
    default_port = 443 if scheme == "https" else 80
    port = explicit_port if explicit_port is not None else default_port

    # Resolve the hostname and then filter the answer set down to publicly
    # routable addresses only. This prevents the request from going to local,
    # reserved, or otherwise policy-disallowed destinations.
    try:
        approved_addresses = resolve_public_host(host, port)
    except (OSError, ValueError) as error:
        return _failure(url, started, error)

    # Request targets preserve the path and query while dropping any fragment,
    # because fragments are not sent to the server over HTTP(S).
    request_target = parsed.path or "/"
    if parsed.query:
        request_target += "?" + parsed.query

    headers = {
        "User-Agent": USER_AGENT,
        "Host": _host_authority(host, port, explicit_port),
        "Connection": "close",
    }

    tls_context = ssl.create_default_context() if scheme == "https" else None
    last_connect_error = None

    # Retry connection establishment across each approved address until one of
    # them succeeds. Once an HTTP request has started, we do not replay the same
    # request and instead fail immediately to avoid duplicate or inconsistent
    # server-side effects.
    for address_info in approved_addresses:
        if scheme == "https":
            connection = PinnedHTTPSConnection(
                host,
                port,
                address_info,
                timeout=timeout,
                context=tls_context,
            )
        else:
            connection = PinnedHTTPConnection(
                host,
                port,
                address_info,
                timeout=timeout,
            )

        try:
            connection.connect()
        except (OSError, http.client.HTTPException) as error:
            # Track the most recent connect failure so the final report can explain
            # why every approved address was rejected.
            last_connect_error = error
            connection.close()
            continue

        try:
            connection.request("GET", request_target, headers=headers)
            response = connection.getresponse()
            try:
                return {
                    "url": url,
                    "status_code": response.status,
                    "headers": dict(response.getheaders()),
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                    "error": None,
                }
            finally:
                response.close()
        except (OSError, http.client.HTTPException) as error:
            return _failure(url, started, error)
        finally:
            connection.close()

    return _failure(
        url,
        started,
        last_connect_error or OSError("All approved destinations failed to connect"),
    )
