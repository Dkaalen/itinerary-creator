"""Compatibility facade for persistent QA report helpers."""

from __future__ import annotations

from shared.source_rows import clean_text, edit_row_id, source_text

from itinerary_generation.qa_report_builder import build_qa_report
from itinerary_generation.qa_report_edits import collect_edit_events
from itinerary_generation.qa_report_helpers import (
    _block_text,
    _clean,
    _event_action,
    _product_family,
    _row_generated_value,
    _row_id,
    _source_text,
)
from itinerary_generation.qa_report_model import (
    DEFAULT_QA_REPORT_DIR,
    QA_SCHEMA_VERSION,
    QaEditEvent,
    QaReport,
    QaWarningEvent,
    qa_reports_dir,
)
from itinerary_generation.qa_report_persistence import persist_qa_report
from itinerary_generation.qa_report_rendering import render_qa_report_json, render_qa_report_markdown
from itinerary_generation.qa_report_warnings import (
    _legacy_editor_state_warnings,
    _row_lookup,
    _warning_from_any,
    collect_warning_events,
)

__all__ = (
    "QA_SCHEMA_VERSION",
    "DEFAULT_QA_REPORT_DIR",
    "QaEditEvent",
    "QaWarningEvent",
    "QaReport",
    "qa_reports_dir",
    "_clean",
    "_block_text",
    "_row_id",
    "_source_text",
    "clean_text",
    "edit_row_id",
    "source_text",
    "_product_family",
    "_event_action",
    "_row_generated_value",
    "collect_edit_events",
    "_row_lookup",
    "_warning_from_any",
    "_legacy_editor_state_warnings",
    "collect_warning_events",
    "build_qa_report",
    "render_qa_report_markdown",
    "render_qa_report_json",
    "persist_qa_report",
)
