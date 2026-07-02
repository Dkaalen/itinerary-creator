"""Summarize Local Library read results for user-facing status."""

from __future__ import annotations

from dataclasses import dataclass

from calculator.library_store import LocalLibraryReadResult


@dataclass(frozen=True)
class LocalLibraryReadSummary:
    """Human-readable status for one Local Library read."""

    level: str
    headline: str
    detail: str
    component_text: str
    total_rows: int
    fetchable_rows: int


def summarize_local_library_read(read_result: LocalLibraryReadResult) -> LocalLibraryReadSummary:
    """Return concise UI copy that makes Google Sheets fallback visible."""

    total_rows = len(read_result.rows)
    fetchable_rows = _autocomplete_row_count(read_result)
    if read_result.source == "google_sheets" and not read_result.read_only:
        return LocalLibraryReadSummary(
            level="success",
            headline=f"Local Library: Google Sheets connected · {fetchable_rows}/{total_rows} fetchable lines.",
            detail="Autocomplete suggestions are reading from the shared Google Sheet.",
            component_text=f"Google Sheets connected ({fetchable_rows} fetchable lines).",
            total_rows=total_rows,
            fetchable_rows=fetchable_rows,
        )

    reason = read_result.message or "Google Sheets is not configured."
    return LocalLibraryReadSummary(
        level="warning",
        headline=f"Local Library fallback active · {fetchable_rows} bundled lines.",
        detail=f"Autocomplete is using the bundled read-only fixture because {reason}",
        component_text=f"Local Library fallback active ({fetchable_rows} bundled lines). {reason}",
        total_rows=total_rows,
        fetchable_rows=fetchable_rows,
    )


def _autocomplete_row_count(read_result: LocalLibraryReadResult) -> int:
    if read_result.source == "fixture":
        return sum(1 for row in read_result.rows if not row.is_deleted and (row.search_text or row.travel_element))
    return sum(1 for row in read_result.rows if row.is_available_for_fetch)
