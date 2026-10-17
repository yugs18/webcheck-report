import argparse, sys
from datetime import datetime, timezone
from pathlib import Path

from webcheck.http_client import check_url # type: ignore
from webcheck.report import create_report, save_report # type: ignore
from webcheck.url_validator import validate_url # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a website and generate a JSON report."
    )
    parser.add_argument("url", help="HTTP or HTTPS URL to check")
    parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    if not validate_url(args.url):
        print("Error: Invalid HTTP/HTTPS URL.", file=sys.stderr)
        return 2

    result = check_url(args.url)
    report = create_report(result)

    output_path = args.output
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        output_path = f"reports/report-{timestamp}.json"

    try:
        save_report(report, output_path)
    except OSError as error:
        print(f"Error saving report: {error}", file=sys.stderr)
        return 1

    print(f"URL: {result['url']}")
    print(f"HTTP status: {result['status_code']}")
    print(f"Response time: {result['elapsed_seconds']} seconds")

    if result["error"]:
        print(f"Error: {result['error']}")

    print(f"Report saved to: {Path(output_path)}")

    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
