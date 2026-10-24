# WebCheck Report

WebCheck Report is a Python command-line tool that checks HTTP/HTTPS endpoints and creates structured JSON diagnostic reports. It is also a practical project for learning Python, networking, HTTP, secure programming, testing, and product development.

> **Project status:** Early-stage CLI prototype. Application-level Phase 2 hardening has been reviewed for manual checks of authorized public URLs. This is not production-hardened and must not be used as a security boundary for arbitrary or untrusted URLs. Passing tests are evidence of expected behavior, not a security certification.

## Features

- **HTTP/HTTPS checks:** Sends a `GET` request and records the status code, response headers, elapsed time, and any error. It does not download the response body.
- **URL validation:** Validates HTTP/HTTPS URL syntax and rejects unsupported or malformed input before making a request.
- **Hostname normalization:** Normalizes DNS hostnames to lowercase ASCII IDNA form, preserves a trailing dot, and handles IPv4/IPv6 literals separately.
- **Destination filtering:** Resolves a hostname and accepts only addresses that pass the global-unicast policy. In addition to Python's `ipaddress` classification, the policy explicitly rejects multicast, scoped IPv6, loopback, link-local, private, unspecified, and reserved address types.
- **Pinned TCP connections:** Connects directly to a selected, approved `getaddrinfo()` socket address rather than resolving the original hostname again inside the HTTP transport.
- **HTTPS verification:** Uses a default client TLS context and the original hostname for TLS server identity and certificate hostname verification.
- **Redirect reporting:** Reports a redirect status and its headers without automatically following the redirect.
- **Connection retries:** Tries subsequent approved address candidates when connection establishment fails, within the remaining timeout budget.
- **Bounded DNS wait:** Uses a fixed maximum of four background resolver jobs and stops waiting when the remaining DNS budget expires. A system resolver call that ignores its own timeout can continue in a daemon thread and hold its slot; the number of resolver threads remains bounded.
- **Timeout input validation:** The client API rejects non-numeric, boolean, non-finite, non-positive, and greater-than-300-second timeout values.
- **Standalone CLI supervisor:** The CLI waits at most 10 seconds for a check, emits a timeout report if the work has not returned, and exits without waiting for its daemon check thread. This bounds the CLI process entry point; it does not turn `check_url()` into a forcibly cancellable operation for a long-running embedded caller.
- **JSON reports:** Saves a report with a UTC generation timestamp; supports a custom output path.
- **CLI exit codes:** Distinguishes invalid URL syntax from operational/request or report-writing failures.
- **Standard-library implementation:** No third-party runtime or test dependencies are required.

## How it works

1. Validate the supplied URL and parse its scheme, hostname, path, query, and port.
2. Normalize the hostname and reject embedded URL credentials or an invalid port.
3. Resolve the hostname into socket-address candidates while bounding how long the caller waits for DNS.
4. Filter candidates using the explicit destination policy: require `is_global`, reject multicast and scoped addresses, and explicitly reject prohibited special address properties; fail if no candidates remain.
5. Attempt direct connections to the approved socket addresses without asking the HTTP transport to perform another DNS lookup.
6. For HTTPS, wrap the connected socket with TLS using the original hostname and the default certificate-verification context.
7. Send a `GET` request, collect response status and headers, then close the response and connection.
8. Save the result in a timestamped JSON report.

## Destination policy and transport behavior

The current policy **filters** prohibited candidates from mixed DNS answers. A destination must pass `ipaddress` global-reachability classification and must not be multicast, scoped, unspecified, loopback, link-local, private, or reserved. IPv4-mapped IPv6 addresses are evaluated using the embedded IPv4 address. If no approved candidates remain, the check fails. A mixed answer is not automatically rejected when it contains at least one approved candidate; this is an explicit policy choice.

The connection is pinned to an approved numeric socket address to avoid a second hostname lookup during TCP connection establishment. This reduces a time-of-check/time-of-use risk, but it does **not** prove resistance to every SSRF or DNS-rebinding scenario.

The client connects directly and intentionally does not use environment-configured HTTP proxies. It does not follow redirects. If redirect support is added in the future, every redirect destination must be parsed and validated independently before any new connection is attempted. The client currently accepts a URL-specified destination port; a deployment that processes untrusted URLs must enforce its own outbound port allowlist, typically TCP 80/443 unless other ports are explicitly required.

## Requirements

- Python 3.12.4 or newer is the intended baseline. The `ipaddress` module's global/private classification changed in Python 3.12.4 and 3.13; run the test suite on every Python version you intend to support.
- A terminal.
- DNS and network access to check public destinations.
- Git is recommended for version control.
- The project currently uses only Python's standard library. `requirements.txt` is intentionally empty apart from explanatory comments.

## Installation

Clone the repository and enter the project directory:

```bash
git clone <your-repository-url>
cd webcheck-report
```

Create and activate a virtual environment on Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No `pip install` step is required while the project remains standard-library-only.

## Usage

Check an HTTP or HTTPS URL:

```bash
python -m webcheck https://example.com
```

Choose the JSON report path explicitly:

```bash
python -m webcheck https://example.com --output reports/example.json
```

By default, a report is written under `reports/` with a UTC timestamp in its filename. The terminal summary prints the URL, HTTP status, elapsed time, any error, and the report location.

### Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | The check produced a response without a tool-level error. An HTTP status such as `404` is still a valid diagnostic result. |
| `1` | The request/check failed operationally, or the report could not be saved. |
| `2` | The supplied URL failed the CLI's initial URL syntax validation. |

A failed network check is still represented in a JSON report when report writing succeeds. Invalid URL syntax is rejected before a report is generated.

### Optional HTTP status failure policy

By default, WebCheck Report preserves its existing behavior: receiving an HTTP response does not itself cause a nonzero exit code. This includes responses such as `404 Not Found` and `500 Internal Server Error`.

The optional `--except-status` argument enables status-based failure handling. When enabled, HTTP `4xx` and `5xx` responses cause exit code `1` unless their status codes are explicitly excepted. HTTP `2xx` and `3xx` responses do not fail this status policy.

For example, allow `404` while treating other `4xx` and `5xx` responses as failures:

```bash
python -m webcheck https://example.com --except-status 404
```

Multiple exceptions can be supplied:

```bash
python -m webcheck https://example.com \
  --except-status 404 \
  --except-status 429
```

When a status-based failure occurs, the CLI still saves the JSON report if writing succeeds. The report retains the actual HTTP status and keeps `error` as `null`, because an HTTP response was received. The CLI's status policy affects its exit code and diagnostic message; it does not rewrite the underlying HTTP result.

If `--except-status` is omitted, existing exit-code behavior is unchanged. Operational failures such as DNS, connection, TLS, timeout, and report-writing errors continue to use their existing failure behavior.

## Timing and timeout semantics

WebCheck Report records `elapsed_seconds` as the wall-clock duration of a check attempt, measured with a monotonic performance clock.

For a completed check, this duration includes URL validation, DNS resolution, connection attempts, TLS negotiation where applicable, and HTTP response-status and header processing. It excludes report creation and JSON file writing.

### Library timeout

The `check_url()` function accepts a positive, finite timeout in seconds, subject to the implementation's configured maximum.

The timeout is an operation budget, not a guarantee that every underlying blocking operation can be forcibly interrupted at the exact deadline. DNS waiting is bounded from the caller's perspective, but a system resolver call may continue in a bounded daemon thread after the caller times out. Blocking network operations can also overrun the deadline before the overrun is detected.

When an operation fails or a response arrives after the deadline, the result records the failure rather than treating a late response as a successful check.

### CLI supervisor timeout

The standalone CLI applies a separate 10-second wait limit to the check worker. When that limit expires, the CLI produces a timeout result and attempts to save it as a JSON report.

The 10-second limit applies to waiting for the check result, not to the entire command process. Report generation and file writing occur afterward and can add time.

The CLI supervisor does not make `check_url()` forcibly cancellable for applications that import and call it directly. Long-running services should use a killable worker-process boundary and enforce outbound network restrictions before accepting untrusted URLs.

## Example JSON report

```json
{
  "generated_at": "2026-10-20T15:00:00+00:00",
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

The values above are illustrative. The actual status, headers, elapsed time, and error depend on the destination and network conditions.

## JSON result contract

Each check result contains the following fields:

| Field | Type | Meaning |
|---|---|---|
| `url` | String | URL supplied for the check |
| `status_code` | Integer or `null` | HTTP status code when an HTTP response is received |
| `headers` | Object | Response headers, or an empty object when no HTTP response is received |
| `elapsed_seconds` | Number | Wall-clock duration of the check, measured in seconds |
| `error` | String or `null` | Operational failure message, or `null` when an HTTP response is received |

A saved JSON report wraps the result in an object containing `generated_at`, an ISO 8601 UTC timestamp, and `result`, the check-result object.

### HTTP status behavior

WebCheck Report records the HTTP status returned by the server. It does not automatically follow redirects or treat HTTP error status codes as transport failures.

- **2xx:** The server returned a successful HTTP response.
- **3xx:** The redirect status and response headers are returned. The redirect is not followed.
- **4xx and 5xx:** The HTTP status and response headers are returned as diagnostic results. The status alone does not populate the tool-level `error` field.

### Operational failure behavior

When the checker cannot obtain an HTTP response—for example, due to DNS resolution failure, connection failure, TLS verification failure, or a timeout—the result uses `status_code: null`, an empty `headers` object, and a descriptive `error` string.

### Compatibility expectations

The five result fields above form the required result shape. Their meanings should remain stable. Changes to field names, data types, or the distinction between HTTP responses and operational failures should be treated as changes to the public output contract and accompanied by corresponding tests and documentation updates.

JSON consumers should not infer that a website is healthy merely because a check returned an HTTP response. For example, a `503` response indicates that the server responded but reported a service-unavailable condition.

## Tests

Run the complete `unittest` suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The suite covers URL validation, public-IP filtering, mixed DNS answers, IPv4/IPv6 classification edge cases including multicast and scoped addresses, bounded DNS wait, pinned socket destinations, request construction, redirect handling, connection retry and cleanup behavior, hostname normalization/IDNA, timeout input/deadline behavior, CLI/report behavior, and TLS validation. A GitHub Actions workflow runs the suite on Python 3.12, 3.13, and 3.14; successful local verification alone does not prove those CI jobs have passed.

Local HTTPS integration tests use test-only certificate fixtures to verify that a trusted certificate with a matching subject alternative name succeeds, while an untrusted certificate and a trusted certificate with a mismatching name are rejected. These are local test certificates only; certificate verification must not be disabled to make a test pass.

Run the full suite in the current checkout before committing or releasing changes. The number of tests can change as the suite evolves, so the command output from the current checkout is the source of truth for the latest test count.

## Project structure

```text
webcheck-report/
├── README.md
├── ROADMAP.md
├── SECURITY_DEPLOYMENT.md
├── SECURITY_REVIEW_PHASE2.md
├── .github/
│   └── workflows/
│       └── tests.yml
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
    ├── fixtures/
    │   ├── ca.crt
    │   ├── server.crt
    │   ├── server.key
    │   ├── wrong-server.crt
    │   └── wrong-server.key
    ├── test_cli.py
    ├── test_hostname_policy.py
    ├── test_http_client.py
    ├── test_https_integration.py
    ├── test_network_safety.py
    ├── test_report.py
    └── test_url_validator.py
```

The fixture names reflect the HTTPS integration test setup. Keep these private test keys restricted to the test environment; never reuse them for a real server.

## Security considerations and known limitations

WebCheck Report is an early-stage diagnostics tool, **not a production-hardened security scanner**. Use it only with systems you own or are explicitly authorized to test.

- **IP classification:** The policy uses Python's `ipaddress` classification plus explicit exclusions for multicast and scoped addresses. The standard-library classification can change between Python releases; support only versions tested by the project. Address classification cannot account for every operating-system route, NAT, firewall, transparent proxy, or unusual network configuration.
- **Mixed DNS answers:** Non-global results are filtered; mixed answers do not cause the entire hostname to be rejected. Only retained, approved socket-address records should be used for connection attempts.
- **DNS and timeouts:** The client API operation budget starts before DNS. The caller stops waiting for `getaddrinfo()` when the remaining budget expires, and at most four background resolver calls can be outstanding. The system resolver call itself cannot be forcibly cancelled safely and may continue occupying one bounded daemon-thread slot. Socket timeout settings apply to individual blocking operations, not a strict total wall-clock deadline; a slow peer that continually sends small amounts of data can exceed the budget before an overrun is detected. The standalone CLI adds a 10-second supervisor wait and then exits; `check_url()` used directly inside a long-running process does not forcibly cancel the operation. The 300-second maximum applies to the client API; the CLI currently uses its fixed 10-second limit.
- **Connection retries:** Only approved candidates are eligible for retries. Retry behavior and cleanup should remain covered by regression tests as the transport changes.
- **TLS:** HTTPS uses a default SSL context and the original hostname for certificate verification. Do not suppress certificate errors or disable hostname verification.
- **Redirects:** Redirects are returned as responses and are not followed. Future redirect support would require independent destination validation for every hop.
- **Proxy behavior:** The custom transport connects directly and ignores environment-configured HTTP proxy settings. This is intentional, but users behind a proxy may not be able to use the tool as expected.
- **IDNA:** Hostname normalization uses Python's built-in `idna` codec. Its behavior is not a claim of complete support for every IDNA standard/profile.
- **Defense in depth:** The application does not enforce OS/container network egress rules. If the tool is ever run as a service or accepts URLs from untrusted users, isolate it and enforce outbound network policy outside the Python process (for example, with a firewall or container/network namespace). Permit only the protocols and destinations required by the product.

A passing test suite does not establish production security or guarantee protection against every SSRF, DNS-rebinding, routing, NAT, IPv4/IPv6 translation, or infrastructure-level scenario. The application-level Phase 2 review is complete for the current manual CLI use case, but the tool is still not suitable as a standalone security boundary for untrusted URL input. A killable per-check process boundary for service usage and enforced network egress restrictions remain deployment-level/security-architecture requirements before accepting untrusted URLs.

## Development principles

1. Understand the problem before adding complexity.
2. Keep modules focused and changes small enough to review.
3. Add regression tests for bugs and security-sensitive behavior.
4. Never claim a security guarantee that the implementation and tests have not established.
5. Keep secrets, virtual environments, and generated reports out of Git.
6. Use only authorized targets and avoid unnecessary network traffic.
7. Prefer reliable functionality over feature count.
8. Validate real user demand before investing in larger product infrastructure.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for current milestones and [SECURITY_DEPLOYMENT.md](SECURITY_DEPLOYMENT.md) for the deployment gate that must be satisfied before accepting untrusted URL input.

## License

No license has been selected yet. Until a license is added, do not assume the project grants permission to redistribute or reuse its code.
