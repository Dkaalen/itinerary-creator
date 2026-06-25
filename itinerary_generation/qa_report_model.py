"""QA report dataclasses and storage constants."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

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
