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
        return LocalLibraryReadSummary("error", "Local Library unavailable", read_result.message, "Local Library unavailable", total, fetchable)
    return LocalLibraryReadSummary("success", f"Local Excel Library · {fetchable} fetchable lines.", "Autocomplete uses the bundled repository workbook only.", f"Local Excel Library ({fetchable} fetchable lines).", total, fetchable)
