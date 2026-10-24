"""Shared data shapes used by WebCheck Report."""

from typing import TypedDict


class CheckResult(TypedDict):
    """Stable result structure returned by a website check."""

    url: str
    status_code: int | None
    headers: dict[str, str]
    elapsed_seconds: float
    error: str | None


class Report(TypedDict):
    """JSON report containing generation metadata and a check result."""

    generated_at: str
    result: CheckResult