"""Summarize Local Library read results for user-facing status."""
from __future__ import annotations
from dataclasses import dataclass
from calculator.library_store import LocalLibraryReadResult

@dataclass(frozen=True)
class LocalLibraryReadSummary:
    level: str
    headline: str
    detail: str
    component_text: str
    total_rows: int
    fetchable_rows: int

def summarize_local_library_read(read_result: LocalLibraryReadResult) -> LocalLibraryReadSummary:
    total = len(read_result.rows)
    fetchable = sum(1 for row in read_result.rows if row.is_available_for_fetch)
    if read_result.message:
        return LocalLibraryReadSummary(
            "error",
            "Local Library unavailable",
            read_result.message,
            "Local Library unavailable",
            total,
            fetchable,
        )
    invalid_count = sum(1 for issue in read_result.diagnostics if issue.category == "invalid_record")
    warning_count = sum(1 for issue in read_result.diagnostics if issue.category == "warning")
    detail = "Autocomplete uses the bundled repository workbook only."
    if invalid_count or warning_count:
        parts = []
        if invalid_count:
            parts.append(f"{invalid_count} invalid row{'s were' if invalid_count != 1 else ' was'} skipped")
        if warning_count:
            parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
        detail = f"{detail} {'; '.join(parts)}."
    level = "warning" if invalid_count or warning_count else "success"
    return LocalLibraryReadSummary(
        level,
        f"Local Excel Library · {fetchable} fetchable lines.",
        detail,
        f"Local Excel Library ({fetchable} fetchable lines).",
        total,
        fetchable,
    )
