"""Pure export-state helpers for the Streamlit PDF flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from ui.picture_workflow import pictures_are_added


@dataclass(frozen=True)
class ExportReadiness:
    """User-facing export gate state for the final PDF page."""

    has_document: bool
    pictures_added: bool
    image_bank_ready: bool
    pending_editor_commit: bool
    pdf_ready: bool
    can_create_pdf: bool
    blocking_messages: tuple[str, ...]
    status_label: str

    def as_dict(self) -> dict[str, object]:
        return {
            "has_document": self.has_document,
            "pictures_added": self.pictures_added,
            "image_bank_ready": self.image_bank_ready,
            "pending_editor_commit": self.pending_editor_commit,
            "pdf_ready": self.pdf_ready,
            "can_create_pdf": self.can_create_pdf,
            "blocking_messages": list(self.blocking_messages),
            "status_label": self.status_label,
        }


def export_readiness_from_state(state: Mapping[str, Any], image_status: Mapping[str, Any] | None = None) -> ExportReadiness:
    """Build a deterministic export decision from session-like state.

    This function intentionally avoids Streamlit calls so the PDF page rules can
    be regression-tested without rendering the app. A PDF can be created only
    after the document exists, pictures have been added, the real image bank is
    available, and the visual editor is not waiting to commit pending changes.
    """

    image_status = image_status or {}
    has_document = bool(state.get("itinerary_html") and state.get("parsed_rows"))
    output_edits = state.get("output_edits") or {}
    pictures = pictures_are_added(output_edits)
    image_ready = image_bank_is_ready_for_client_pictures(image_status)
    pending_commit = bool(state.get("_pdf_after_visual_edit_commit_nonce")) and not bool(
        state.get("_visual_editor_export_commit_ready")
    )
    current_signature = state.get("preview_signature")
    pdf_ready = bool(
        (state.get("pdf_bytes") and state.get("pdf_signature") == current_signature)
        or (state.get("export_pdf_bytes") and state.get("export_pdf_signature") == current_signature)
    )

    blocking: list[str] = []
    if not has_document:
        blocking.append("Generate an itinerary before exporting.")
    if not pictures:
        blocking.append("Add and review destination pictures before creating the PDF.")
    if not image_ready:
        blocking.append("Connect the real destination image bank before creating the PDF.")
    if pending_commit:
        blocking.append("Applying pending editor changes before PDF creation.")

    can_create = has_document and pictures and image_ready and not pending_commit
    if pdf_ready:
        status = "PDF ready"
    elif blocking:
        status = "Not ready"
    else:
        status = "Ready to create"

    return ExportReadiness(
        has_document=has_document,
        pictures_added=pictures,
        image_bank_ready=image_ready,
        pending_editor_commit=pending_commit,
        pdf_ready=pdf_ready,
        can_create_pdf=can_create,
        blocking_messages=tuple(blocking),
        status_label=status,
    )
