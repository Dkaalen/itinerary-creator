"""Pure export-state helpers for the Streamlit PDF flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.pdf_artifact_state import pdf_artifact_is_current
from app_modules.pdf_preflight import build_pdf_preflight_report
from ui.picture_workflow import pictures_are_added


@dataclass(frozen=True)
class ExportReadiness:
    """User-facing export gate state for the final PDF page."""

    has_document: bool
    pictures_added: bool
    image_bank_ready: bool
    pdf_ready: bool
    can_create_pdf: bool
    blocking_messages: tuple[str, ...]
    status_label: str
    preflight_status: str = "Clear"
    preflight_issues: tuple[str, ...] = field(default_factory=tuple)
    critical_issue_count: int = 0
    review_issue_count: int = 0
    advisory_issue_count: int = 0
    client_risk_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "has_document": self.has_document,
            "pictures_added": self.pictures_added,
            "image_bank_ready": self.image_bank_ready,
            "pdf_ready": self.pdf_ready,
            "can_create_pdf": self.can_create_pdf,
            "blocking_messages": list(self.blocking_messages),
            "status_label": self.status_label,
            "preflight_status": self.preflight_status,
            "preflight_issues": list(self.preflight_issues),
            "critical_issue_count": self.critical_issue_count,
            "review_issue_count": self.review_issue_count,
            "advisory_issue_count": self.advisory_issue_count,
            "client_risk_count": self.client_risk_count,
        }


def export_readiness_from_state(state: Mapping[str, Any], image_status: Mapping[str, Any] | None = None) -> ExportReadiness:
    """Build a deterministic export decision from session-like state.

    This function intentionally avoids Streamlit calls so the PDF page rules can
    be regression-tested without rendering the app. A PDF can be created only
    after the document exists, pictures have been added, a usable image source is
    available. PDF export uses the last server-saved editor state.
    """

    image_status = image_status or {}
    has_document = bool(state.get("itinerary_html") and state.get("parsed_rows"))
    output_edits = state.get("output_edits") or {}
    pictures = pictures_are_added(output_edits)
    image_ready = image_bank_is_ready_for_client_pictures(image_status)
    pdf_ready = pdf_artifact_is_current(state)

    blocking: list[str] = []
    if not has_document:
        blocking.append("Generate an itinerary before exporting.")
    if not pictures:
        blocking.append("Add destination pictures before creating the PDF.")
    if not image_ready:
        blocking.append("Connect the real destination image bank before creating the PDF.")
    preflight = build_pdf_preflight_report(state, image_status)
    for issue in preflight.issues:
        if issue.severity == "critical" and issue.message not in blocking:
            blocking.append(issue.message)

    can_create = has_document and pictures and image_ready and not pdf_ready and preflight.can_export
    if blocking:
        status = "Not ready"
    elif pdf_ready:
        status = "PDF ready"
    else:
        status = "Ready to create"

    return ExportReadiness(
        has_document=has_document,
        pictures_added=pictures,
        image_bank_ready=image_ready,
        pdf_ready=pdf_ready,
        can_create_pdf=can_create,
        blocking_messages=tuple(blocking),
        status_label=status,
        preflight_status=preflight.status_label,
        preflight_issues=tuple(issue.message for issue in preflight.issues),
        critical_issue_count=preflight.critical_count,
        review_issue_count=preflight.review_count,
        advisory_issue_count=preflight.advisory_count,
        client_risk_count=sum(1 for issue in preflight.issues if str(issue.code).startswith("client_") or issue.code == "client_output_warning"),
    )
