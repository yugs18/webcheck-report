# WebCheck Report

A Python command-line tool for checking public HTTP/HTTPS endpoints and generating structured JSON diagnostic reports.

WebCheck Report is an independent software project being built from scratch to develop practical skills in Python, networking, HTTP, software testing, secure programming, and product development.

> **Project status:** Early development — CLI prototype implemented, 21 automated tests passing.

## Features

- **URL validation:** Checks URL structure, supported schemes, hostname presence, whitespace, and port validity.
- **HTTP diagnostics:** Sends HTTP GET requests and records response status codes, response headers, and elapsed time.
- **Network safety checks:** Resolves destination addresses and rejects destinations that resolve to non-public IP addresses.
- **Redirect handling:** Reports HTTP redirects without automatically following them.
- **Error handling:** Handles invalid URLs, DNS resolution failures, connection failures, and timeouts.
- **JSON reports:** Saves diagnostic results with a UTC timestamp.
- **Command-line interface:** Runs checks directly from the terminal.
- **Automated tests:** Tests URL validation, HTTP behavior, network safety, report generation, and CLI behavior.

## How It Works

The current workflow is:

1. Accept a URL from the command line.
2. Validate the URL structure.
3. Resolve the hostname and check the resulting IP addresses.
4. Send an HTTP GET request if the destination passes the network safety check.
5. Capture the status code, response headers, elapsed time, and any error.
6. Create a timestamped JSON report.
7. Save the report and display a summary in the terminal.

## Requirements

- Python 3.12 or a compatible Python version.
- A terminal.
- Internet connectivity for checking public endpoints.
- Git, for version control.

## Installation

Clone the repository and enter the project directory:

```bash
git clone <your-repository-url>
cd webcheck-report
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on Linux:

```bash
source .venv/bin/activate
```

The project currently uses Python's standard library, so no third-party runtime dependencies are required.

## Usage

Check a public HTTP/HTTPS URL:

```bash
python -m webcheck https://example.com
```

Save the report to a specific location:

```bash
python -m webcheck https://example.com --output reports/example.json
```

The tool prints a summary containing the URL, HTTP status, elapsed time, any error, and the report location.

By default, reports are saved under `reports/` with timestamped filenames.

### Exit Codes

| Exit code | Meaning |
|---|---|
| `0` | The check produced a diagnostic result without a tool-level error. |
| `1` | The check encountered an operational error, such as a network failure. |
| `2` | The supplied URL is invalid. |

An HTTP error status, such as `404`, is still a valid diagnostic result and does not by itself mean the tool failed.

## Example Report Structure

A generated JSON report has this general structure:

```json
{
  "generated_at": "UTC timestamp",
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

The values above illustrate the report format; actual response headers, status codes, and timings depend on the destination.

## Running Tests

Run the complete test suite:

```bash
python -m unittest discover -s tests -v
```

The current suite contains 21 tests covering:

- URL validation.
- Successful HTTP responses.
- HTTP error responses.
- Connection errors.
- Redirect handling.
- Non-public destination rejection.
- DNS resolution edge cases.
- JSON report generation and saving.
- CLI exit codes and error reporting.

**Current verified result:** All 21 tests pass.

## Project Structure

```text
webcheck-report/
├── .gitignore
├── README.md
├── ROADMAP.md
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

Generated reports, Python cache files, and the virtual environment are excluded from version control.

## Security Considerations and Limitations

WebCheck Report is an early-stage diagnostic tool, not a production-hardened security scanner.

- Use it only to check systems you own or are explicitly authorized to test.
- The current network safety check rejects hostnames that resolve to non-public IP addresses.
- DNS is resolved during validation, and the HTTP client may resolve the hostname again when connecting. This creates a potential DNS-rebinding or time-of-check/time-of-use risk that has not yet been eliminated.
- Redirects are not automatically followed, reducing the risk of silently reaching an unintended destination.
- Network-level restrictions and connection-time destination enforcement are still needed before the tool can be considered robust against server-side request forgery (SSRF) scenarios.
- A passing test suite does not establish production security.

Do not treat the current network checks as a substitute for a properly isolated execution environment or enforced network egress restrictions.

## Development Philosophy

The project is being built incrementally:

1. Understand each component before adding complexity.
2. Write testable, modular Python code.
3. Validate behavior with automated tests.
4. Document security assumptions and limitations.
5. Build useful functionality before introducing unnecessary infrastructure.
6. Validate real user demand before investing in a larger product.

## Long-Term Goal

Develop WebCheck Report into a useful, reliable web diagnostics product that can potentially be distributed or commercialized.

Potential future directions include richer reports, multiple-target checks, monitoring, historical comparisons, and a user-friendly interface. These are possibilities, not current features or guaranteed commitments.

The immediate priority is to make the CLI reliable, address its security limitations, improve its usability, and validate whether real users would pay for the functionality.

See [ROADMAP.md](ROADMAP.md) for planned development.

## License

No license has been selected yet. Until one is added, do not assume the project grants permission to redistribute or reuse its code.
