"""Markdown reporting for Vipin corpus evaluations."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.vipin_corpus.models import BadOutput


def write_markdown_report(
    summary: Mapping[str, Any],
    path: str | Path,
    *,
    bad_jsonl_path: str | Path | None = None,
    report_label: str | None = None,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bad_outputs = list(summary.get("bad_outputs") or [])
    sample_by_category: dict[str, list[Any]] = defaultdict(list)
    priority = [
        "blank_title",
        "overlong_title",
        "activity_text_used_as_title",
        "activity_text_used_as_generated_title",
        "missing_parsed_city",
        "missing_activity_title",
        "unexpected_skip",
        "missing_source_type",
        "non_itinerary_type",
    ]
    for bad_output in bad_outputs:
        category = bad_output.category if isinstance(bad_output, BadOutput) else str(dict(bad_output).get("category", ""))
        if len(sample_by_category[category]) < 6:
            sample_by_category[category].append(bad_output)
    resolved_report_label = report_label or ("INPUT5" if "input5" in output_path.name.lower() else "INPUT4")
    lines = [
        f"# {resolved_report_label} Vipin Excel Corpus Regression Report",
        "",
        "Purpose: run the real messy Nordic calculator corpus through parser and editable-title generation, then log risky outputs for regression hardening.",
        "",
        "## Summary",
        "",
        f"- Corpus rows checked: {summary.get('item_count', 0)}",
        f"- Parsed output rows: {summary.get('parsed_count', 0)}",
        f"- Generated editable titles checked: {summary.get('generated_count', 0)}",
        f"- Workbooks: {len(summary.get('file_counts', {}))}",
        f"- Sheets with extracted rows: {summary.get('sheet_count', 0)}",
        f"- Parser exceptions: {summary.get('parse_errors', 0)}",
        f"- Rows skipped by parser: {summary.get('skipped_count', 0)}",
        f"- Average parser confidence: {summary.get('average_confidence', 0)}%",
        f"- Rows under 80 confidence: {summary.get('under_80_confidence_count', 0)}",
        f"- Whole-corpus generation smoke: {'passed' if summary.get('bulk_generation_ok') else 'failed'}",
    ]
    if summary.get("bulk_generation_error"):
        lines.append(f"- Whole-corpus generation error: `{summary.get('bulk_generation_error')}`")
    if bad_jsonl_path:
        lines.append(f"- Bad-output log: `{Path(bad_jsonl_path).as_posix()}`")
    lines.extend(["", "## Bad-output counts", ""])
    for category, count in (summary.get("bad_output_counts") or {}).items():
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Parser review flags", ""])
    for flag, count in (summary.get("parser_flag_counts") or {}).items():
        lines.append(f"- {flag}: {count}")
    lines.extend(["", "## Top source types", ""])
    for row_type, count in (summary.get("type_counts") or {}).items():
        lines.append(f"- {row_type or '[blank]'}: {count}")
    lines.extend(["", "## Worst-case samples", ""])
    categories = [category for category in priority if sample_by_category.get(category)]
    categories.extend(category for category in sample_by_category if category not in categories)
    if not categories:
        lines.append("No bad outputs detected by the configured heuristics.")
    else:
        for category in categories:
            lines.append(f"### {category}")
            for bad in sample_by_category[category]:
                data = bad.as_dict() if isinstance(bad, BadOutput) else dict(bad)
                lines.append(
                    f"- {data.get('source_id')} | "
                    f"type={data.get('source_type')!r} | title={data.get('parsed_title')!r} | "
                    f"generated={data.get('generated_title')!r} | reason={data.get('reason')}"
                )
            lines.append("")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
