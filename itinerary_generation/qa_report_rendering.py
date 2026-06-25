"""Render persistent QA reports to Markdown or JSON."""

from __future__ import annotations

import json

from itinerary_generation.qa_report_model import QaReport


def render_qa_report_markdown(report: QaReport) -> str:
    lines = [
        "# Itinerary QA Report",
        "",
        f"Generated: {report.generated_at}",
        f"App version: {report.app_version or 'unknown'}",
        f"Draft ID: {report.draft_id}",
        f"Report ID: {report.report_id}",
        "",
        "## Summary",
        f"- Parsed rows: {report.summary.get('row_count', 0)}",
        f"- Edited items: {report.summary.get('edited_items', 0)}",
        f"- Warnings: {report.summary.get('warnings', 0)}",
        f"- Product/title/source risk warnings: {report.summary.get('product_mismatch_risks', 0)}",
        "",
    ]
    lines.append("## Edited Items")
    if not report.edits:
        lines.extend(["No manual edits were detected against the generated output.", ""])
    for index, event in enumerate(report.edits, start=1):
        lines.extend([
            f"### {index}. {event.location}",
            f"- Type: {event.event_type}",
            f"- Field: {event.field or 'n/a'}",
            f"- Source row ID: {event.source_row_id or 'n/a'}",
            f"- Product family: {event.product_family or 'n/a'}",
            "",
            "Original/generated value:",
            "```text",
            event.original_text or "n/a",
            "```",
            "User/current value:",
            "```text",
            event.edited_text or "n/a",
            "```",
            "Source snippet:",
            "```text",
            event.source_text or "n/a",
            "```",
            f"Suggested developer action: {event.suggested_action}",
            "",
        ])
    lines.append("## Warnings")
    if not report.warnings:
        lines.extend(["No warnings were recorded.", ""])
    for index, event in enumerate(report.warnings, start=1):
        lines.extend([
            f"### {index}. {event.location or event.code}",
            f"- Code: {event.code}",
            f"- Message: {event.message}",
            f"- Day: {event.day or 'n/a'}",
            f"- City: {event.city or 'n/a'}",
            f"- Section: {event.section or 'n/a'}",
            f"- Source row IDs: {', '.join(event.source_row_ids) if event.source_row_ids else 'n/a'}",
            "",
            "Source snippet:",
            "```text",
            event.source_text or "n/a",
            "```",
            f"Suggested action: {event.suggested_action}",
            "",
        ])
    return "\n".join(lines).strip() + "\n"


def render_qa_report_json(report: QaReport) -> str:
    return json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
