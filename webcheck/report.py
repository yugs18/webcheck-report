import json
from datetime import datetime, timezone
from pathlib import Path

def create_report(result: dict) -> dict:
    """Build the report document from a check result.

    ``generated_at`` records when the report was assembled as a timezone-aware
    UTC ISO 8601 timestamp. The original result is stored intact under
    ``result`` so consumers can distinguish report metadata from check data.
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


def save_report(report: dict, output_path: str) -> None:
    """Write a report as indented UTF-8 JSON, creating parent directories.

    Existing files at ``output_path`` are overwritten. Filesystem and
    serialization errors are allowed to propagate so the caller can report
    that saving failed instead of treating an unwritten report as success.
    """
    path = Path(output_path)
    # Create missing parent folders (including nested folders) before opening
    # the file; this is a no-op when the destination directory already exists.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use a context manager to close the file even if serialization raises.
    with path.open("w", encoding="utf-8") as file:
        # Indentation makes reports readable; ensure_ascii=False preserves
        # international text directly instead of escaping it as Unicode codes.
        json.dump(report, file, indent=2, ensure_ascii=False)
        # A trailing newline is conventional for text files and CLI-generated data.
        file.write("\n")
