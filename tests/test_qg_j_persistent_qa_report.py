from pathlib import Path

from itinerary_generation.qa_report import (
    build_qa_report,
    persist_qa_report,
    render_qa_report_json,
    render_qa_report_markdown,
)


def test_qa_report_records_row_edit_and_warning_with_source_context(tmp_path):
    rows = [
        {
            "row_id": "row_1",
            "day": "Day 5",
            "effective_type": "Activity",
            "type": "Activity",
            "city": "Rovaniemi",
            "title": "Northern Lights Hunt",
            "source_text": "Rovaniemi: Northern Lights Hunt by Minibus at the Arctic Circle | meeting point Arctic City Snowmobile Park",
            "activity_product": {"canonical_family": "Northern Lights Hunt"},
            "includes": ["Guide", "Warm juice"],
        }
    ]
    output_edits = {
        "draft_id": "draft-test",
        "rows": {
            "row_1": {
                "title": "Snowmobile Evening Safari & Aurora Opportunity",
                "includes_text": "Guide\nWarm juice",
            }
        },
    }
    warnings = [
        {
            "code": "activity_title_source_mismatch",
            "message": "Product title may not match source.",
            "page_label": "Day 5 · Rovaniemi · Evening Experience",
            "source_row_ids": ["row_1"],
        }
    ]

    report = build_qa_report(rows, output_edits, app_version="test", warnings=warnings)

    assert report.summary["edited_items"] == 1
    assert report.summary["warnings"] == 1
    assert report.edits[0].day == "Day 5"
    assert report.edits[0].source_row_id == "row_1"
    assert "Northern Lights Hunt" in report.edits[0].source_text
    assert report.warnings[0].location == "Day 5 · Rovaniemi · Evening Experience"

    markdown = render_qa_report_markdown(report)
    json_text = render_qa_report_json(report)

    assert "# Itinerary QA Report" in markdown
    assert "Snowmobile Evening Safari" in markdown
    assert "activity_title_source_mismatch" in markdown
    assert '"schema_version"' in json_text

    paths = persist_qa_report(report, tmp_path)
    assert Path(paths["json_path"]).exists()
    assert Path(paths["markdown_path"]).exists()
    assert Path(paths["index_path"]).exists()


def test_qa_report_is_empty_but_valid_without_manual_edits():
    rows = [{"row_id": "r1", "day": "Day 1", "effective_type": "Transfer", "city": "Oslo", "title": "Private transfer"}]
    report = build_qa_report(rows, {"draft_id": "clean"}, app_version="test", warnings=[])

    assert report.summary["edited_items"] == 0
    assert report.summary["warnings"] == 0
    assert "No manual edits" in render_qa_report_markdown(report)
