"""Helpers for packaging and persisting check results as structured JSON.

This module sits at the boundary between runtime validation and report output: it
adds report metadata and writes the final document to disk in a readable and
portable format. Keeping these responsibilities separate makes the rest of the
project easier to reason about and allows the same result object to be reused for
multiple output targets.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def create_report(result: dict) -> dict:
    """Build a report payload from a single check result.

    A report is not just the raw check result; it also includes a timestamp that
    marks when the report was assembled. Adding this metadata makes the report
    self-describing and helps downstream tooling correlate output files with the
    time they were generated.

    Args:
        result: A dictionary returned by the HTTP check logic, such as the URL,
            status code, headers, elapsed time, and error message.

    Returns:
        A dictionary containing a UTC ISO 8601 timestamp and the original result
        under the ``result`` key.
    """
    # Using timezone-aware UTC time ensures the report is comparable across
    # environments and not dependent on local machine clock settings.
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


def save_report(report: dict, output_path: str) -> None:
    """Persist a report dictionary as indented UTF-8 JSON.

    The function ensures the destination directory exists before writing and uses
    ``json.dump`` with indentation so the output is easy to inspect by hand or in
    a text editor. Existing files at the target path are overwritten, which is a
    convenient behavior for generated reports that are meant to reflect the latest
    check results.

    Args:
        report: The report dictionary to serialize.
        output_path: A filesystem path where the JSON document should be written.

    Raises:
        OSError: If the parent directory cannot be created or the file cannot be
            opened/written.
        TypeError: If the report cannot be serialized as JSON.
    """
    path = Path(output_path)

    # Create missing parent folders before writing. This is especially useful for
    # nested output paths such as ``reports/daily/site.json`` where the directory
    # may not yet exist.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use a context manager to guarantee the file is closed even if the JSON dump
    # fails midway through serialization.
    with path.open("w", encoding="utf-8") as file:
        # Pretty-printing improves readability for humans, and ensure_ascii=False
        # keeps non-ASCII text intact instead of escaping it to \uXXXX sequences.
        json.dump(report, file, indent=2, ensure_ascii=False)

        # A trailing newline is conventional for generated text files and makes the
        # output cleaner when viewed in terminal editors or diffs.
        file.write("\n")
