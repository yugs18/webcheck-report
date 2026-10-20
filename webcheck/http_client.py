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
import math
import socket
import ssl
import threading
import time
from urllib.parse import urlparse

from webcheck.url_validator import validate_url  # type: ignore

# Use a stable identifier for outbound requests so servers can recognize the
# tool if they log incoming traffic. Keeping this constant centralized makes it
# easy to maintain if the project wants a different user-agent in future.
USER_AGENT = "WebCheckReport/0.1"
_MAX_OPERATION_TIMEOUT_SECONDS = 300.0

# ``socket.getaddrinfo`` is a blocking system resolver call and has no timeout
# parameter. Run a small, globally bounded number of these calls in daemon
# threads so the caller can stop waiting after its DNS budget expires. A resolver
# call that ignores its own system timeout may continue in the background, but
# it retains a slot; repeated stalled lookups therefore cannot create an
# unbounded number of resolver threads.
_MAX_PENDING_DNS_LOOKUPS = 4
_DNS_LOOKUP_SLOTS = threading.BoundedSemaphore(_MAX_PENDING_DNS_LOOKUPS)


def _validate_timeout(timeout: float) -> float:
    """Return a finite positive timeout or raise a clear ValueError."""
    message = (
        "Timeout must be a finite positive number no greater than "
        f"{_MAX_OPERATION_TIMEOUT_SECONDS:g} seconds"
    )
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError(message)
    try:
        numeric_timeout = float(timeout)
    except (OverflowError, ValueError):
        raise ValueError(message) from None
    if (
        not math.isfinite(numeric_timeout)
        or numeric_timeout <= 0
        or numeric_timeout > _MAX_OPERATION_TIMEOUT_SECONDS
    ):
        raise ValueError(message)
    return numeric_timeout


def _bounded_getaddrinfo(host: str, port: int, timeout: float):
    """Wait at most ``timeout`` seconds for a bounded background DNS lookup.

    Python's system resolver cannot be forcibly cancelled safely. If it outlives
    this wait, its daemon thread keeps one of the small, fixed number of resolver
    slots until the call finishes. This bounds caller wait time and thread growth,
    but does not claim to terminate a resolver call that has already started.
    """
    timeout = _validate_timeout(timeout)
    wait_started = time.monotonic()

    if not _DNS_LOOKUP_SLOTS.acquire(timeout=timeout):
        raise TimeoutError("DNS resolution timed out waiting for a resolver slot")

    completed = threading.Event()
    outcome = {}

    def lookup():
        try:
            outcome["addresses"] = socket.getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        except Exception as error:
            outcome["error"] = error
        finally:
            completed.set()
            _DNS_LOOKUP_SLOTS.release()

    worker = threading.Thread(
        target=lookup,
        name="webcheck-dns-lookup",
        daemon=True,
    )
    try:
        worker.start()
    except Exception:
        _DNS_LOOKUP_SLOTS.release()
        raise

    remaining = timeout - (time.monotonic() - wait_started)
    if remaining <= 0 or not completed.wait(remaining):
        raise TimeoutError("DNS resolution timed out")

    error = outcome.get("error")
    if error is not None:
        raise error
    return outcome["addresses"]


def is_approved_public_ip(value: str) -> bool:
    """Allow globally reachable unicast addresses without IPv6 scope IDs.

    ``is_global`` is necessary but not sufficient for this tool's destination
    policy: multicast addresses can be classified as global. Scoped IPv6
    addresses are rejected because a zone identifier makes the target depend
    on a local interface and is not appropriate for this public-target policy.
    IPv4-mapped IPv6 addresses use the embedded IPv4 address's classification.
    """
    # Zone identifiers are local-interface-specific (for example, "%eth0").
    # Reject them before parsing/classifying so even a scoped global IPv6 literal
    # cannot pass the policy.
    if not isinstance(value, str) or "%" in value:
        return False

    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False

    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            address = address.ipv4_mapped

    return (
        address.is_global
        and not address.is_multicast
        and not address.is_unspecified
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_private
        and not address.is_reserved
    )


def resolve_public_host(host: str, port: int, timeout: float = 10.0):
    """Return only DNS results whose resolved IP addresses are globally routable.

       This function filters DNS results to retain only addresses approved
        by the destination policy. If no approved addresses remain, it
        rejects the hostname. Mixed answers can therefore retain public
        candidates while excluding private or otherwise disallowed ones.

        This filtering is one defense-in-depth measure, not a complete
        guarantee against every SSRF or network-routing risk.

    Args:
        host: Hostname or literal IP address to resolve.
        port: Port to use when resolving and connecting.

    Returns:
        A list of ``getaddrinfo`` tuples that passed the public-address check.

    Raises:
        OSError: If the host does not resolve to any IPs at all.
        ValueError: If no resolved address is globally routable.
        TimeoutError: If DNS resolution or waiting for resolver capacity exceeds
            the supplied timeout. A timed-out system resolver call may continue
            in a bounded daemon thread until the operating system returns.
    """
    # ``getaddrinfo`` produces tuples shaped like:
    # (family, type, proto, canonname, sockaddr)
    # The sockaddr for IPv4 is a 2-tuple (ip, port); for IPv6 it is a 4-tuple
    # containing the address and flow info/ scope id.
    addresses = _bounded_getaddrinfo(host, port, timeout)
    if not addresses:
        raise OSError("Hostname did not resolve to an IP address")

    approved_addresses = []
    for address in addresses:
        # Read the numeric IP from the sockaddr payload. For IPv6, the separate
        # scope-id field can carry a zone/interface even when the address string
        # contains no "%"; reject that metadata as well as scoped text literals.
        sockaddr = address[4]
        ip_text = sockaddr[0]
        if (
            address[0] == socket.AF_INET6
            and len(sockaddr) >= 4
            and sockaddr[3] != 0
        ):
            continue

        if is_approved_public_ip(ip_text):
            approved_addresses.append(address)

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

def normalize_hostname(host):
    """Normalize a DNS hostname to ASCII IDNA form, rejecting scoped literals."""
    if not host:
        raise ValueError("Hostname is required")

    # Reject '%' before trying ipaddress parsing: Python accepts zone-scoped
    # IPv6 literals, but this client intentionally does not support them.
    if "%" in host:
        raise ValueError("Scoped IP literals are not supported")

    # IP literals must not be sent through IDNA conversion.
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass

    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Invalid internationalized hostname") from exc

    if len(ascii_host) > 253:
        raise ValueError("Hostname is too long")

    labels = ascii_host[:-1].split(".") if ascii_host.endswith(".") else ascii_host.split(".")

    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not all(char.isalnum() or char == "-" for char in label)
        for label in labels
    ):
        raise ValueError("Invalid hostname label")

    return ascii_host

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

def _remaining_timeout(deadline):
    """Return the remaining operation budget or raise when exhausted."""
    remaining = deadline - time.monotonic()

    if remaining <= 0:
        raise TimeoutError("Operation deadline exceeded")

    return remaining


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
        timeout: Positive, finite best-effort total time budget in seconds. DNS
            resolution is bounded from the caller's perspective, and socket
            operations use the remaining budget. Python's blocking HTTP/TLS
            operations are still not forcibly interruptible at an exact wall-clock
            deadline; a slow peer can exceed the budget before the overrun is
            detected. A timed-out system resolver call may continue in a daemon
            thread, with global concurrency bounded by ``_MAX_PENDING_DNS_LOOKUPS``.

    Returns:
        A dictionary with the URL, optional status code, response headers, timing,
        and any error text. A successful request returns a numeric status code;
        failures return ``None`` for the status and a human-readable error.
    """
    started = time.perf_counter()

    try:
        timeout = _validate_timeout(timeout)
    except ValueError as error:
        return _failure(url, started, error)

    # Start the operation budget before DNS so resolution does not sit outside
    # the timeout contract.
    deadline = time.monotonic() + timeout

    # Validate the input string before performing any DNS or socket operations.
    # This immediately rejects malformed or unsupported URL values.
    if not validate_url(url):
        return _failure(url, started, "Invalid HTTP/HTTPS URL")

    try:
        parsed = urlparse(url)
        host = normalize_hostname(parsed.hostname)
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
        approved_addresses = resolve_public_host(
            host,
            port,
            timeout=_remaining_timeout(deadline),
        )
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

    for address_info in approved_addresses:
        try:
            remaining = _remaining_timeout(deadline)
        except TimeoutError as error:
            return _failure(url, started, error)

        if scheme == "https":
            connection = PinnedHTTPSConnection(
                host,
                port,
                address_info,
                timeout=remaining,
                context=tls_context,
            )
        else:
            connection = PinnedHTTPConnection(
                host,
                port,
                address_info,
                timeout=remaining,
            )

        try:
            connection.connect()
        except (OSError, http.client.HTTPException) as error:
            last_connect_error = error
            connection.close()
            continue

        try:
            remaining = _remaining_timeout(deadline)
            connection.sock.settimeout(remaining)

            connection.request("GET", request_target, headers=headers)

            remaining = _remaining_timeout(deadline)
            connection.sock.settimeout(remaining)

            response = connection.getresponse()
            try:
                # A response can arrive after the remaining budget expires. Check
                # before accepting it, but always close it even when that check
                # raises TimeoutError.
                _remaining_timeout(deadline)
                return {
                    "url": url,
                    "status_code": response.status,
                    "headers": dict(response.getheaders()),
                    "elapsed_seconds": round(
                        time.perf_counter() - started, 4
                    ),
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
