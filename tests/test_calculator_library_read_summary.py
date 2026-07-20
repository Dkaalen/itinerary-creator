from calculator.library_model import LocalLibraryRow
from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult

def test_summary_reports_local_excel_workbook():
    result = LocalLibraryReadResult((LocalLibraryRow(travel_element="Hotel"),), "local_excel", True)
    summary = summarize_local_library_read(result)
    assert summary.level == "success"
    assert summary.fetchable_rows == 1
    assert summary.component_text == "Local Excel Library (1 fetchable lines)."
    assert "workbook only" in summary.detail

def test_summary_reports_actionable_workbook_error():
    result = LocalLibraryReadResult((), "local_excel", True, "Local Library workbook is missing")
    summary = summarize_local_library_read(result)
    assert summary.level == "error"
    assert summary.detail == "Local Library workbook is missing"
