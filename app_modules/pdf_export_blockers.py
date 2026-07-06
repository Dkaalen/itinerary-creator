"""User-facing blockers for PDF export."""

from __future__ import annotations

import streamlit as st

from app_modules.export_issue_display import show_issue_list
from itinerary_generation.output_contract import validate_output_layout_contract
from itinerary_generation.quality_gate import evaluate_client_output_quality


def preview_contract_blocks_pdf(html: str, expected_day_count: int, *, clear_pdf_artifact) -> bool:
    """Render preview-structure blockers and return whether export must stop."""

    contract_issues = validate_output_layout_contract(html, expected_day_count=expected_day_count)
    blocking_contract_issues = [issue for issue in contract_issues if issue.severity == "error"]
    if not blocking_contract_issues:
        return False
    clear_pdf_artifact("Blocked by preview structure")
    show_issue_list("PDF export stopped because the preview structure is invalid.", blocking_contract_issues)
    return True


def client_safety_blocks_pdf(pdf_render_context, image_matches: dict, image_bank_status: dict, *, clear_pdf_artifact) -> bool:
    """Render client-safety blockers and return whether export must stop."""

    client_safety_report = evaluate_client_output_quality(
        pdf_render_context.render_document,
        day_images=image_matches,
        image_bank_status=image_bank_status,
    )
    if not client_safety_report.is_blocked:
        return False
    clear_pdf_artifact("Blocked by client safety check")
    st.error("PDF export stopped because client-facing output contains a fatal issue.")
    for issue in client_safety_report.blocking_issues:
        st.error(issue.message)
    return True


__all__ = ["client_safety_blocks_pdf", "preview_contract_blocks_pdf"]
