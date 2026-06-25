"""Build persistent QA report objects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from itinerary_generation.qa_report_edits import collect_edit_events
from itinerary_generation.qa_report_model import QA_SCHEMA_VERSION, QaReport
from itinerary_generation.qa_report_warnings import _legacy_editor_state_warnings, collect_warning_events


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
    digest_source = json.dumps({
        "draft_id": draft_id,
        "edits": [asdict(e) for e in edits],
        "warnings": [asdict(w) for w in warning_events],
    }, ensure_ascii=False, sort_keys=True)
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
