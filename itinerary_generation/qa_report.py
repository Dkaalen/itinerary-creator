"""Persistent QA report and edit-learning-log helpers.

The report is intentionally lightweight: it compares the current editable output
state with the generated/source rows that already exist in memory, then writes a
small JSON/Markdown report to shared app storage.  It does not re-run itinerary
generation or call external services.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.titles import create_client_activity_title, create_day_title
from itinerary_generation.render_text_helpers import list_to_text
from itinerary_generation.editable_draft import section_by_id
from itinerary_generation.source_identity import clean_text, edit_row_id, source_text

QA_SCHEMA_VERSION = 1
DEFAULT_QA_REPORT_DIR = "qa_reports"


@dataclass(frozen=True)
class QaEditEvent:
    event_type: str
    location: str
    day: str = ""
    city: str = ""
    section: str = ""
    field: str = ""
    original_text: str = ""
    edited_text: str = ""
    source_text: str = ""
    source_row_id: str = ""
    product_family: str = ""
    suggested_action: str = ""


@dataclass(frozen=True)
class QaWarningEvent:
    code: str
    message: str
    location: str = ""
    day: str = ""
    city: str = ""
    section: str = ""
    source_text: str = ""
    source_row_ids: tuple[str, ...] = ()
    suggested_action: str = "Review this location against the supplier input."


@dataclass(frozen=True)
class QaReport:
    schema_version: int
    generated_at: str
    app_version: str
    draft_id: str
    report_id: str
    summary: dict[str, Any]
    edits: tuple[QaEditEvent, ...] = field(default_factory=tuple)
    warnings: tuple[QaWarningEvent, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "app_version": self.app_version,
            "draft_id": self.draft_id,
            "report_id": self.report_id,
            "summary": self.summary,
            "edits": [asdict(event) for event in self.edits],
            "warnings": [asdict(event) for event in self.warnings],
        }


def qa_reports_dir() -> Path:
    return Path(os.environ.get("ITINERARY_QA_REPORT_DIR", DEFAULT_QA_REPORT_DIR)).expanduser()


def _clean(value: Any) -> str:
    return clean_text(value)


def _block_text(value: Any, *, limit: int = 800) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _row_id(row: Mapping[str, Any], fallback_index: int = 0) -> str:
    return edit_row_id(row, fallback_index)


def _source_text(row: Mapping[str, Any] | None) -> str:
    text = source_text(
        row,
        ("source_text", "raw_text", "description_raw", "original_text", "input_text"),
        separator=" ",
        first_non_empty=True,
        limit=800,
    )
    if text:
        return text
    return _block_text(source_text(row, ("original_title", "title"), separator=" ", first_non_empty=True))


def _product_family(row: Mapping[str, Any]) -> str:
    fingerprint = row.get("activity_product") if isinstance(row.get("activity_product"), Mapping) else {}
    return str(
        row.get("canonical_family")
        or fingerprint.get("canonical_family")
        or row.get("product_family")
        or ""
    ).strip()


def _event_action(field: str, row_type: str = "") -> str:
    if field == "title":
        return "Review source fidelity and product fingerprinting for this item."
    if field in {"client_description", "intro", "blocks_html"}:
        return "Review the generated wording for missing, over-generic, or incorrect client-facing text."
    if field in {"includes_text", "whats_included", "whats_not_included"}:
        return "Review inclusion/exclusion extraction and optional-status handling."
    if row_type.lower() in {"activity", "cruise", "ferry"}:
        return "Review activity normalization and supplier product matching."
    return "Review why the generated value needed a manual edit."


def _row_generated_value(row: Mapping[str, Any], field: str) -> str:
    row_type = get_row_type(dict(row))
    if field == "title":
        return create_client_activity_title(dict(row)) if row_type == "Activity" else str(row.get("title", ""))
    if field == "includes_text":
        return list_to_text(row.get("includes", []))
    if field == "notable_sights_text":
        return list_to_text(row.get("notable_sights", []))
    return str(row.get(field, ""))


def collect_edit_events(parsed_rows: Iterable[Mapping[str, Any]], output_edits: Mapping[str, Any]) -> tuple[QaEditEvent, ...]:
    rows = [dict(row) for row in parsed_rows or []]
    grouped = group_rows_by_day(rows)
    events: list[QaEditEvent] = []
    day_edits = output_edits.get("days", {}) if isinstance(output_edits.get("days"), Mapping) else {}

    for day, day_rows in grouped.items():
        edits = day_edits.get(day, {}) if isinstance(day_edits.get(day), Mapping) else {}
        if not edits:
            continue
        generated = {
            "title": create_day_title(day_rows),
            "city": create_travel_route_label(day_rows) or get_primary_city(day_rows),
            "intro": create_day_intro(day_rows, detail_level=output_edits.get("detail_level", "Rich descriptive")),
        }
        for field_name, original in generated.items():
            if field_name not in edits:
                continue
            edited = str(edits.get(field_name, ""))
            if _clean(edited) == _clean(original):
                continue
            city = str(edits.get("city") or generated.get("city") or get_primary_city(day_rows))
            events.append(QaEditEvent(
                event_type="day_edit",
                location=f"{day} · {city} · Day {field_name}",
                day=day,
                city=city,
                section="Day header" if field_name in {"title", "city"} else "Day intro",
                field=field_name,
                original_text=_block_text(original),
                edited_text=_block_text(edited),
                source_text=_block_text(" | ".join(_source_text(row) for row in day_rows[:3] if _source_text(row))),
                suggested_action=_event_action(field_name),
            ))
        if "blocks_html" in edits:
            events.append(QaEditEvent(
                event_type="visual_day_block_edit",
                location=f"{day} · {edits.get('city') or get_primary_city(day_rows)} · Visual page content",
                day=day,
                city=str(edits.get("city") or get_primary_city(day_rows)),
                section="Visual page content",
                field="blocks_html",
                original_text="Generated day content block",
                edited_text=_block_text(edits.get("blocks_html", "")),
                source_text=_block_text(" | ".join(_source_text(row) for row in day_rows[:3] if _source_text(row))),
                suggested_action=_event_action("blocks_html"),
            ))

    row_edits = output_edits.get("rows", {}) if isinstance(output_edits.get("rows"), Mapping) else {}
    editable_fields = (
        "title", "city", "time", "duration", "client_description", "meeting_point",
        "end_point", "luggage_included", "hotel_name", "hotel_nights", "room_category",
        "meal_plan", "notable_sights_text", "includes_text",
    )
    for row in rows:
        row_id = _row_id(row)
        edits = row_edits.get(row_id, {}) if isinstance(row_edits.get(row_id), Mapping) else {}
        if not edits:
            continue
        row_type = get_row_type(row)
        day = str(row.get("day", "")).strip()
        city = str(edits.get("city") or row.get("city") or "").strip()
        for field_name in editable_fields:
            if field_name not in edits:
                continue
            original = _row_generated_value(row, field_name)
            edited = str(edits.get(field_name, ""))
            if _clean(edited) == _clean(original):
                continue
            events.append(QaEditEvent(
                event_type="row_edit",
                location=f"{day} · {city} · {row_type} · {field_name}",
                day=day,
                city=city,
                section=row_type,
                field=field_name,
                original_text=_block_text(original),
                edited_text=_block_text(edited),
                source_text=_source_text(row),
                source_row_id=row_id,
                product_family=_product_family(row),
                suggested_action=_event_action(field_name, row_type),
            ))

    final_fields = {
        "whats_included_text": "What's included",
        "whats_included_html": "What's included",
        "whats_included_pages_html": "What's included",
        "whats_not_included_text": "What's not included",
        "whats_not_included_html": "What's not included",
        "important_travel_notes_text": "Important travel notes",
    }
    for field_name, section in final_fields.items():
        if output_edits.get(field_name):
            events.append(QaEditEvent(
                event_type="final_page_edit",
                location=f"Final pages · {section}",
                section=section,
                field=field_name,
                original_text="Generated final-page content",
                edited_text=_block_text(output_edits.get(field_name)),
                suggested_action=_event_action("whats_included" if "included" in field_name else field_name),
            ))

    flags = output_edits.get("visual_editor_issue_flags") if isinstance(output_edits.get("visual_editor_issue_flags"), list) else []
    for flag in flags:
        if not isinstance(flag, Mapping):
            continue
        events.append(QaEditEvent(
            event_type="editor_issue_flag",
            location=str(flag.get("label") or flag.get("key") or "Visual editor issue"),
            section="Visual editor",
            field=str(flag.get("key", "")),
            original_text=_block_text(flag.get("original", "")),
            edited_text=_block_text(flag.get("corrected", "")),
            suggested_action="Review the flagged visual-editor correction and add a regression test if it reflects a generator mistake.",
        ))

    return tuple(events)


def _row_lookup(parsed_rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {_row_id(row, index): row for index, row in enumerate(parsed_rows or []) if isinstance(row, Mapping)}


def _warning_from_any(warning: Any, row_by_id: Mapping[str, Mapping[str, Any]]) -> QaWarningEvent | None:
    if warning is None:
        return None
    if isinstance(warning, str):
        return QaWarningEvent(code="warning", message=warning, location="General")
    if isinstance(warning, Mapping):
        code = str(warning.get("code") or "warning")
        message = str(warning.get("message") or warning.get("excerpt") or code)
        source_ids = tuple(str(value) for value in warning.get("source_row_ids", []) if value)
        row = row_by_id.get(source_ids[0]) if source_ids else None
        return QaWarningEvent(
            code=code,
            message=message,
            location=str(warning.get("page_label") or warning.get("location") or "Review warning"),
            day=str(warning.get("day") or (row or {}).get("day", "")),
            city=str(warning.get("city") or (row or {}).get("city", "")),
            section=str(warning.get("section") or get_row_type(dict(row)) if row else ""),
            source_text=_source_text(row) if row else _block_text(warning.get("source_text", "")),
            source_row_ids=source_ids,
            suggested_action=str(warning.get("suggested_action") or "Review this warning on the named itinerary page before export."),
        )
    code = str(getattr(warning, "code", "warning"))
    message = str(getattr(warning, "message", warning))
    return QaWarningEvent(code=code, message=message, location=str(getattr(warning, "context", "General") or "General"))



def _legacy_editor_state_warnings(output_edits: Mapping[str, Any]) -> tuple[QaWarningEvent, ...]:
    """Warn when typed editor state suppresses stale legacy final-page keys.

    Patch AZ made typed final sections authoritative for preview/PDF parity. This
    QA warning makes the compatibility mirror visible to developers so stale
    legacy HTML can be cleaned from saved drafts instead of silently lingering.
    """

    if not isinstance(output_edits, Mapping):
        return ()
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits.get("editor_draft"), Mapping) else {}
    if not editor_draft:
        return ()

    checks = (
        (
            "whats_included",
            "What’s included",
            ("whats_included_pages_html", "whats_included_html", "whats_included_text"),
        ),
        (
            "whats_not_included",
            "What’s not included",
            ("whats_not_included_html", "whats_not_included_text"),
        ),
    )
    warnings: list[QaWarningEvent] = []
    for section_id, label, legacy_keys in checks:
        if not section_by_id(editor_draft, section_id):
            continue
        stale_keys = tuple(key for key in legacy_keys if output_edits.get(key))
        if not stale_keys:
            continue
        warnings.append(QaWarningEvent(
            code="typed_editor_suppressed_legacy_final_section",
            message=f"Typed editor draft owns {label}; stale legacy keys were ignored for preview/PDF: {', '.join(stale_keys)}.",
            location=f"Final pages · {label}",
            section=label,
            suggested_action="Clean the stale legacy final-page keys from the saved draft or keep relying on the typed editor_draft section.",
        ))
    return tuple(warnings)

def collect_warning_events(parsed_rows: Iterable[Mapping[str, Any]], warnings: Iterable[Any] | None) -> tuple[QaWarningEvent, ...]:
    row_by_id = _row_lookup(parsed_rows)
    events: list[QaWarningEvent] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings or []:
        event = _warning_from_any(warning, row_by_id)
        if not event:
            continue
        key = (event.code, event.message, event.location)
        if key in seen:
            continue
        seen.add(key)
        events.append(event)
    return tuple(events)


def build_qa_report(
    parsed_rows: Iterable[Mapping[str, Any]],
    output_edits: Mapping[str, Any] | None,
    *,
    app_version: str = "",
    warnings: Iterable[Any] | None = None,
) -> QaReport:
    rows = [dict(row) for row in parsed_rows or []]
    output_edits = output_edits or {}
    edits = collect_edit_events(rows, output_edits)
    warning_events = collect_warning_events(rows, warnings) + _legacy_editor_state_warnings(output_edits)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    draft_id = str(output_edits.get("draft_id") or "no-draft")
    digest_source = json.dumps({"draft_id": draft_id, "edits": [asdict(e) for e in edits], "warnings": [asdict(w) for w in warning_events]}, ensure_ascii=False, sort_keys=True)
    report_id = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:12]
    summary = {
        "row_count": len(rows),
        "edited_items": len(edits),
        "warnings": len(warning_events),
        "product_mismatch_risks": len([w for w in warning_events if "product" in w.code or "title" in w.code or "source" in w.code]),
    }
    return QaReport(
        schema_version=QA_SCHEMA_VERSION,
        generated_at=generated_at,
        app_version=app_version,
        draft_id=draft_id,
        report_id=report_id,
        summary=summary,
        edits=edits,
        warnings=warning_events,
    )


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


def persist_qa_report(report: QaReport, base_dir: Path | None = None) -> dict[str, str]:
    base = base_dir or qa_reports_dir()
    base.mkdir(parents=True, exist_ok=True)
    safe_stamp = report.generated_at.replace(":", "").replace("+", "Z")
    stem = f"qa_report_{safe_stamp}_{report.report_id}"
    json_path = base / f"{stem}.json"
    md_path = base / f"{stem}.md"
    json_text = render_qa_report_json(report)
    md_text = render_qa_report_markdown(report)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    index_path = base / "index.jsonl"
    with index_path.open("a", encoding="utf-8") as index_file:
        index_file.write(json.dumps({
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "app_version": report.app_version,
            "draft_id": report.draft_id,
            "edited_items": report.summary.get("edited_items", 0),
            "warnings": report.summary.get("warnings", 0),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }, ensure_ascii=False) + "\n")
    return {"json_path": str(json_path), "markdown_path": str(md_path), "index_path": str(index_path)}
