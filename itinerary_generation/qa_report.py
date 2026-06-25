"""Compatibility facade for debug QA reports."""

from __future__ import annotations

from itinerary_generation.qa_report_core import (
    QaEditEvent,
    QaWarningEvent,
    QaReport,
    qa_reports_dir,
    collect_edit_events,
    collect_warning_events,
    build_qa_report,
    render_qa_report_markdown,
    render_qa_report_json,
    persist_qa_report,
)

__all__ = ['QaEditEvent', 'QaWarningEvent', 'QaReport', 'qa_reports_dir', 'collect_edit_events', 'collect_warning_events', 'build_qa_report', 'render_qa_report_markdown', 'render_qa_report_json', 'persist_qa_report']
