from __future__ import annotations

from calculator.library_model import LocalLibraryRow
from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult


def test_local_library_read_summary_reports_google_sheets_connection() -> None:
    result = LocalLibraryReadResult(
        rows=(
            LocalLibraryRow(library_id="fetchable", travel_element="Hotel"),
            LocalLibraryRow(library_id="deleted", is_deleted=True, travel_element="Old hotel"),
        ),
        source="google_sheets",
        read_only=False,
    )

    summary = summarize_local_library_read(result)

    assert summary.level == "success"
    assert summary.total_rows == 2
    assert summary.fetchable_rows == 1
    assert "Google Sheets connected" in summary.headline
    assert summary.component_text == "Google Sheets connected (1 fetchable lines)."


def test_local_library_read_summary_makes_fixture_fallback_visible() -> None:
    result = LocalLibraryReadResult(
        rows=(LocalLibraryRow(library_id="fallback", travel_element="Fallback hotel"),),
        source="fixture",
        read_only=True,
        message="Google service account secrets are missing: private_key",
    )

    summary = summarize_local_library_read(result)

    assert summary.level == "warning"
    assert summary.fetchable_rows == 1
    assert "fallback active" in summary.headline
    assert "1 bundled lines" in summary.headline
    assert "private_key" in summary.detail
    assert "Local Library fallback active" in summary.component_text


def test_local_library_read_summary_counts_fixture_sections_as_autocomplete_rows() -> None:
    result = LocalLibraryReadResult(
        rows=(
            LocalLibraryRow(library_id="section", record_type="section", is_fetchable=False, travel_element="HELSINKI"),
            LocalLibraryRow(library_id="line", record_type="line", is_fetchable=True, travel_element="Helsinki hotel"),
        ),
        source="fixture",
        read_only=True,
    )

    summary = summarize_local_library_read(result)

    assert summary.total_rows == 2
    assert summary.fetchable_rows == 2
    assert "2 bundled lines" in summary.component_text
