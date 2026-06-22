import json

from scripts.vipin_excel_corpus import (
    ExcelCorpusItem,
    collect_excel_corpus_items,
    evaluate_excel_corpus,
    write_bad_outputs_jsonl,
    write_markdown_report,
)


def _item(row_type, element, *, city="Rovaniemi", day="Day 1", row=10, from_date="01/01/2026"):
    return ExcelCorpusItem(
        file="Vipin sample.xlsx",
        sheet="10000",
        row=row,
        day=day,
        row_type=row_type,
        city=city,
        element=element,
        from_date=from_date,
    )


def test_input4_detects_overlong_supplier_activity_title_from_vipin_pattern():
    item = _item(
        "Activity",
        "Visit to Santa Claus Village with lunch, 10:00 DURATION: 7 hours 30 min "
        "Rovaniemi is the Official Hometown of Santa Claus, and the town’s most popular attraction is "
        "Santa Claus Village on the Arctic Circle. Includes lunch and return transfer.",
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_input4_detects_missing_city_even_when_activity_title_is_present():
    item = _item(
        "Activity",
        "A Finntastic Walking Tour in Helsinki | 10:30 AM | 2. 15 Hr | "
        "Professional authorised Helsinki Guide meeting Point: Senate Square",
        city="",
        row=11,
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert summary["bad_output_counts"]["missing_source_city"] == 1
    assert "missing_parsed_city" not in summary["bad_output_counts"]
    assert "missing_city" not in summary["parser_flag_counts"]


def test_input4_logs_blank_type_rows_and_calculator_cost_rows():
    blank_type = _item(
        "",
        "Helsinki: Overnight Cruise to Stockholm - Departure from Helsinki: 5:00 pm - "
        "Arrival to Stockholm: 10:00 am - Includes: Sleeper cabin",
        city="",
        row=12,
    )
    cost_row = _item("per pax", "486.8", city="", row=13)

    summary = evaluate_excel_corpus([blank_type, cost_row])

    assert summary["parse_errors"] == 0
    assert summary["bad_output_counts"]["missing_source_type"] == 1
    assert summary["bad_output_counts"]["non_itinerary_type"] == 1
    assert summary["skipped_count"] == 2


def test_input4_writes_machine_log_and_human_report(tmp_path):
    item = _item(
        "Activity",
        "A Finntastic Walking Tour in Helsinki | 10:30 AM | 2. 15 Hr | "
        "Professional authorised Helsinki Guide meeting Point: Senate Square",
        city="",
    )
    summary = evaluate_excel_corpus([item])
    jsonl_path = tmp_path / "bad.jsonl"
    report_path = tmp_path / "report.md"

    write_bad_outputs_jsonl(summary["bad_outputs"], jsonl_path)
    write_markdown_report(summary, report_path, bad_jsonl_path=jsonl_path)

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["category"] == "missing_source_city" for line in lines)
    report = report_path.read_text(encoding="utf-8")
    assert "INPUT4 Vipin Excel Corpus Regression Report" in report
    assert "missing_source_city" in report
