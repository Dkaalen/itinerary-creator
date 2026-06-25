"""Collect warning events for the persistent QA report."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.editable_draft import section_by_id
from itinerary_generation.qa_report_helpers import _block_text, _row_id, _source_text
from itinerary_generation.qa_report_model import QaWarningEvent


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
    """Warn when typed editor state suppresses stale legacy final-page keys."""

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
