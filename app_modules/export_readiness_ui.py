"""Small export-readiness presentation helpers."""

from __future__ import annotations

from html import escape

from app_modules.export_state import ExportReadiness


def export_readiness_panel_html(readiness: ExportReadiness) -> str:
    """Return compact HTML for the PDF export readiness panel."""

    headline = _headline(readiness)
    body = _body(readiness)
    chips = _chips(readiness)
    return (
        '<div class="export-readiness-panel">'
        '<div class="export-readiness-copy">'
        f'<span>{escape(readiness.status_label)}</span>'
        f'<strong>{escape(headline)}</strong>'
        f'<p>{escape(body)}</p>'
        '</div>'
        '<div class="export-readiness-chips">'
        + ''.join(f'<span>{escape(chip)}</span>' for chip in chips)
        + '</div>'
        '</div>'
    )


def _headline(readiness: ExportReadiness) -> str:
    if readiness.pdf_ready:
        return "Current PDF is ready"
    if readiness.can_create_pdf:
        return "Ready to create the final PDF"
    return "PDF export needs attention"


def _body(readiness: ExportReadiness) -> str:
    if readiness.pdf_ready:
        return "The download matches the current saved preview."
    if readiness.can_create_pdf:
        return "The document, pictures, and export checks are aligned."
    if readiness.blocking_messages:
        return readiness.blocking_messages[0]
    return "Review the checks below before creating the PDF."


def _chips(readiness: ExportReadiness) -> tuple[str, ...]:
    issue_count = readiness.critical_issue_count + readiness.review_issue_count + readiness.advisory_issue_count
    picture_status = "Pictures ready" if readiness.pictures_added else "Pictures missing"
    image_status = "Image source ready" if readiness.image_bank_ready else "Image source missing"
    preflight = f"Preflight · {readiness.preflight_status}"
    if issue_count:
        preflight = f"Preflight · {issue_count} issue{'s' if issue_count != 1 else ''}"
    return (picture_status, image_status, preflight)
