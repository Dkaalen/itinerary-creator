"""Debug QA report data model."""

from __future__ import annotations

from itinerary_generation.qa_report_core import (
    QaEditEvent,
    QaWarningEvent,
    QaReport,
    qa_reports_dir,
)

__all__ = ['QaEditEvent', 'QaWarningEvent', 'QaReport', 'qa_reports_dir']
