# WebCheck Report

WebCheck Report is a Python command-line tool for checking HTTP/HTTPS endpoints and producing structured JSON diagnostic reports. It is also a learning project for Python, networking, HTTP, secure programming, testing, and product development.

> **Project status:** Early-stage CLI prototype. The HTTP transport uses a pinned socket destination and the current automated test suite contains 18 tests. Passing tests are not a security certification.

## Features

- **URL validation:** Checks the URL scheme, hostname, literal whitespace, and port syntax.
- **Destination filtering:** Resolves DNS and retains only socket-address records whose IP address passes Python's `ipaddress.ip_address(...).is_global` classification.
- **Pinned TCP connection:** The HTTP/HTTPS transport connects to a selected approved `getaddrinfo()` socket address rather than asking the transport to resolve the original hostname again.
- **HTTPS identity:** Uses a default client SSL context and the original hostname for TLS server identity and certificate hostname verification.
- **HTTP diagnostics:** Performs a GET request and records the response status, response headers, elapsed time, and errors. It does not download the response body.
- **Redirect behavior:** Returns redirect status and headers without automatically following the redirect.
- **JSON reports:** Writes a timestamped JSON report.
- **CLI behavior:** Provides terminal output and exit codes for URL errors and operational failures.
- **Automated tests:** Covers URL validation, address filtering, pinned connection behavior, TLS hostname handling, redirects, CLI behavior, and report output.

## How it works

1. Validate the input URL.
2. Parse the hostname and effective port.
3. Resolve the hostname into socket-address candidates.
4. Filter the candidates using `ipaddress.ip_address(...).is_global`.
5. Try the approved candidates one at a time, connecting directly to the chosen socket address.
6. For HTTPS, wrap the connected socket with TLS using the original hostname and the default verification context.
7. Send a GET request using the URL path and query, capture response metadata, and close the connection.
8. Save the result in a timestamped JSON report.

### Destination policy

The current policy **filters** non-global candidates from mixed DNS answers. If a result set has both approved and prohibited addresses, the checker retains the approved records and does not attempt the prohibited records. If no approved records remain, the check fails.

This is an intentional policy choice; it is not an assertion that `is_global` alone covers every routing, operating-system, proxy, or SSRF risk. The client makes direct connections and does not use environment-configured HTTP proxies. Redirects are not followed; if redirect handling is added later, each new destination will need independent validation.

## Requirements

- Python 3.12 or newer is the project's target baseline.
- A terminal.
- Network/DNS access to check public destinations.
- Git is recommended for version control.
- The project currently uses only Python's standard library. No third-party runtime or test dependencies are required; `requirements.txt` is intentionally empty apart from explanatory comments.

## Installation

Clone the repository and enter its directory:

```bash
git clone <your-repository-url>
cd webcheck-report
```

Create and activate a virtual environment on Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The standard-library-only project does not need a package-install step. The `requirements.txt` file is included to make the absence of third-party dependencies explicit and to provide a place to record them if that changes later.

## Usage

Check a public HTTP/HTTPS URL:

```bash
python -m webcheck https://example.com
```

Choose a report path:

```bash
python -m webcheck https://example.com --output reports/example.json
```

By default, reports are written under `reports/` with timestamped filenames. The terminal summary includes the URL, HTTP status, response time, any error, and report location.

### Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | The request produced a diagnostic response without a tool-level error. An HTTP status such as `404` is still a valid diagnostic result. |
| `1` | The check failed operationally, or the report could not be saved. |
| `2` | The supplied URL failed the CLI's initial URL syntax validation. |

## Example report

```json
{
  "generated_at": "UTC ISO 8601 timestamp",
  "result": {
    "url": "https://example.com",
    "status_code": 200,
    "headers": {
      "Content-Type": "text/html"
    },
    "elapsed_seconds": 0.25,
    "error": null
  }
}
```

The values are illustrative; real response data depends on the destination.

## Tests

Run the complete standard-library `unittest` suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

**Latest verification for the uploaded source snapshot:** 18 tests passed. A separate local HTTP smoke test in the review environment also returned HTTP 200 and confirmed the request path/query and a single Host header. That one-off smoke test is not currently part of the committed test suite.

The test suite uses mocks for key connection/TLS behaviors. An actual external HTTPS handshake was not verified during this review because DNS resolution for the external test hostname failed in the execution environment. A real TLS integration test remains on the roadmap.

## Project structure

```text
webcheck-report/
├── README.md
├── ROADMAP.md
├── requirements.txt
├── reports/
│   └── .gitkeep
├── webcheck/
│   ├── __init__.py
│   ├── __main__.py
│   ├── http_client.py
│   ├── report.py
│   └── url_validator.py
└── tests/
    ├── test_cli.py
    ├── test_http_client.py
    ├── test_network_safety.py
    ├── test_report.py
    └── test_url_validator.py
```

## Security considerations and limitations

WebCheck Report is an early-stage diagnostic tool, not a production-hardened security scanner.

- Use it only against systems you own or are explicitly authorized to test.
- Address filtering relies on Python's `ipaddress` classification. IPv4/IPv6 special cases and unusual network configurations need further review and tests.
- Mixed public/non-public DNS answers are filtered rather than causing the entire hostname to be rejected. The implementation must continue to connect only to the returned approved records.
- The custom transport makes direct connections and does not honor environment-configured HTTP proxies. This behavior is intentional but should be documented for users operating behind proxies.
- HTTPS uses the default SSL context and supplies the original hostname to TLS. Mocked unit tests do not prove that every real-world TLS/certificate case succeeds; certificate failures must not be bypassed by disabling verification.
- Redirects are not followed. This behavior must not be weakened without validating each redirect destination independently.
- The configured timeout is applied to socket operations; it is not a strict total wall-clock deadline, and system DNS resolution may take additional time.
- IDN/Unicode hostname behavior, expanded IPv6 edge cases, retry/resource-cleanup behavior, and live TLS integration still need additional tests.
- Network egress restrictions and execution isolation provide additional defense in depth.

A passing test suite does not establish production security or prove resistance to every SSRF/DNS-rebinding scenario.

## Development philosophy

1. Understand the problem before adding complexity.
2. Keep modules focused and changes small enough to review.
3. Add regression tests for bugs and security-sensitive behavior.
4. Never claim a security guarantee that the implementation and tests have not established.
5. Keep secrets, virtual environments, and generated reports out of Git.
6. Prefer reliable functionality over feature count.
7. Validate real user demand before investing in larger product infrastructure.

## Long-term goal

The long-term goal is to determine whether a useful, reliable web diagnostics product can be built and distributed. Potential future directions include multiple-target checks, historical comparisons, monitoring, alerts, and a user-friendly interface. These are possibilities, not current capabilities or guaranteed plans.

See [ROADMAP.md](ROADMAP.md) for current milestones.

## License

No license has been selected yet. Until a license is added, do not assume the project grants permission to redistribute or reuse its code.
