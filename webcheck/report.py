"""Helpers for packaging and persisting check results as structured JSON.

This module sits at the boundary between runtime validation and report output: it
adds report metadata and writes the final document to disk in a readable and
portable format. Keeping these responsibilities separate makes the rest of the
project easier to reason about and allows the same result object to be reused for
multiple output targets.
"""

import json
import os
import tempfile
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
    """Atomically save a report as indented UTF-8 JSON.

    The report is serialized before filesystem changes are made. The completed
    temporary file is then atomically moved into place, so a failed write
    does not replace an existing report with incomplete JSON.

    Args:
        report: The report dictionary to serialize.
        output_path: Destination filesystem path.

    Raises:
        OSError: If directory creation, writing, or replacement fails.
        TypeError: If the report cannot be serialized as JSON.
        ValueError: If JSON serialization fails because of invalid data.
    """
    path = Path(output_path)

    # Serialize first so invalid data does not create or truncate a report.
    serialized = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        # Keep the temporary file in the destination directory so replacement
        # happens on the same filesystem.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            file.write(serialized)

        # Replace the destination only after the complete JSON file is written.
        os.replace(temporary_path, path)
        temporary_path = None

    finally:
        # Clean up a temporary file if writing or replacement failed.
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
