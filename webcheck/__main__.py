"""Command-line entry point for the WebCheckReport application."""

import argparse
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from webcheck.http_client import check_url # type: ignore
from webcheck.report import create_report, save_report # type: ignore
from webcheck.url_validator import validate_url # type: ignore


CLI_CHECK_TIMEOUT_SECONDS = 10.0


def _run_check_with_wall_clock_limit(
    url: str, timeout: float = CLI_CHECK_TIMEOUT_SECONDS
) -> dict:
    """Bound the standalone CLI's wait for a single check.

    The check runs in a daemon thread. When the limit expires, the CLI can
    produce a timeout report without waiting for a slow system resolver or
    network operation. The standalone command then exits, which stops its
    daemon threads during interpreter shutdown. This is not a cancellation
    guarantee for callers that import ``check_url`` or ``main`` into a
    long-running process; such services should supervise work in a killable
    worker process and enforce outbound network restrictions.
    """
    started = time.perf_counter()
    completed = threading.Event()
    outcome = {}

    def perform_check():
        try:
            outcome["result"] = check_url(url, timeout=timeout)
        except Exception as error:
            outcome["error"] = error
        finally:
            completed.set()

    worker = threading.Thread(
        target=perform_check,
        name="webcheck-cli-check",
        daemon=True,
    )
    worker.start()

    if not completed.wait(timeout):
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "error": f"CLI wall-clock limit exceeded after {timeout:g} seconds",
        }

    if "error" in outcome:
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "error": f"Unexpected check failure: {outcome['error']}",
        }

    return outcome["result"]


def main() -> int:
    """Run the command-line workflow and return the process exit code.

    The command requires a target URL and optionally accepts a path for the
    JSON report. It validates the input, performs the check, writes the report,
    and prints a short summary for interactive use.

    Exit codes distinguish a successful check (0), a URL-check or file-writing
    failure (1), and invalid URL syntax supplied by the user (2). A failed
    network check is still written to the report before returning code 1.
    """
    # argparse handles --help, missing arguments, and command-line syntax errors.
    parser = argparse.ArgumentParser(
        description="Check a website and generate a JSON report."
    )
    parser.add_argument("url", help="HTTP or HTTPS URL to check")
    parser.add_argument(
        "--output",
        help="Output JSON file path (defaults to a timestamped file in reports/)",
    )

    args = parser.parse_args()

    # Reject malformed input early: no DNS lookup or HTTP request is needed, and
    # the user gets a clear command-line error rather than a generated report.
    if not validate_url(args.url):
        print("Error: Invalid HTTP/HTTPS URL.", file=sys.stderr)
        return 2

    # check_url returns failures (such as timeouts) as result data, allowing the
    # same report format to be written whether the request succeeds or not.
    result = _run_check_with_wall_clock_limit(
        args.url,
        timeout=CLI_CHECK_TIMEOUT_SECONDS,
    )
    report = create_report(result)

    # An explicit --output path is used as given. Otherwise generate a
    # timestamped default path; UTC keeps filenames independent of local time.
    output_path = args.output
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        output_path = f"reports/report-{timestamp}.json"

    # save_report creates parent directories, but filesystem errors can still
    # occur (for example, if the destination is not writable).
    try:
        save_report(report, output_path)
    except OSError as error:
        print(f"Error saving report: {error}", file=sys.stderr)
        return 1

    # Keep terminal output brief; headers and other full result details remain
    # available in the JSON report.
    print(f"URL: {result['url']}")
    print(f"HTTP status: {result['status_code']}")
    print(f"Response time: {result['elapsed_seconds']} seconds")

    # A request failure is printed after the summary and also determines the
    # final non-zero exit code below.
    if result["error"]:
        print(f"Error: {result['error']}")

    print(f"Report saved to: {Path(output_path)}")

    # Report creation succeeding does not mean the website check itself passed.
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
