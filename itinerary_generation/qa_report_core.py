"""Compatibility facade for :mod:`itinerary_generation.qa_report`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.qa_report import (
    QA_SCHEMA_VERSION,
    DEFAULT_QA_REPORT_DIR,
    QaEditEvent,
    QaWarningEvent,
    QaReport,
    qa_reports_dir,
    _clean,
    _block_text,
    _row_id,
    _source_text,
    _product_family,
    _event_action,
    _row_generated_value,
    collect_edit_events,
    _row_lookup,
    _warning_from_any,
    _legacy_editor_state_warnings,
    collect_warning_events,
    build_qa_report,
    render_qa_report_markdown,
    render_qa_report_json,
    persist_qa_report,
)

__all__ = ('QA_SCHEMA_VERSION', 'DEFAULT_QA_REPORT_DIR', 'QaEditEvent', 'QaWarningEvent', 'QaReport', 'qa_reports_dir', '_clean', '_block_text', '_row_id', '_source_text', '_product_family', '_event_action', '_row_generated_value', 'collect_edit_events', '_row_lookup', '_warning_from_any', '_legacy_editor_state_warnings', 'collect_warning_events', 'build_qa_report', 'render_qa_report_markdown', 'render_qa_report_json', 'persist_qa_report',)
