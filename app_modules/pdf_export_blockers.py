"""Technical PDF blockers and non-blocking quality review presentation."""

from __future__ import annotations

from app_modules.export_issue_display import show_issue_list, show_review_issue_list
from itinerary_generation.client_output_quality_gate import add_image_quality_issues
from itinerary_generation.output_contract import validate_output_layout_contract


_TECHNICAL_ROW_VALIDATION_CODES = frozenset({"no_main_itinerary_rows"})


def preview_contract_blocks_pdf(html: str, expected_day_count: int, *, clear_pdf_artifact) -> bool:
    """Render preview-structure blockers and return whether export must stop."""

    contract_issues = validate_output_layout_contract(html, expected_day_count=expected_day_count)
    blocking_contract_issues = [issue for issue in contract_issues if issue.severity == "error"]
    if not blocking_contract_issues:
        return False
    clear_pdf_artifact("Blocked by preview structure")
    show_issue_list("PDF export stopped because the preview structure is invalid.", blocking_contract_issues)
    return True


def row_validation_blocks_pdf(report, *, clear_pdf_artifact) -> bool:
    """Block only when parsed rows cannot produce a renderable document.

    Schedule, continuity, classification, and source-fidelity findings remain
    visible review notes. They do not prevent the advisor from creating a PDF.
    """

    blocking_issues = tuple(getattr(report, "blocking_issues", ()) or ())
    all_issues = tuple(getattr(report, "issues", blocking_issues) or ())
    technical = tuple(
        issue for issue in blocking_issues
        if str(getattr(issue, "code", "") or "") in _TECHNICAL_ROW_VALIDATION_CODES
    )
    advisory = tuple(issue for issue in all_issues if issue not in technical)
    show_review_issue_list(
        "PDF creation can continue. Review the itinerary validation notes before delivery.",
        advisory,
    )
    if not technical:
        return False
    clear_pdf_artifact("Blocked by missing renderable itinerary rows")
    show_issue_list("PDF export stopped because no renderable itinerary is available.", technical)
    return True


def show_client_quality_review(pdf_render_context, image_matches: dict, image_bank_status: dict):
    """Show prepared output findings as review notes and return the report.

    The quality engine retains its original severities for QA and reporting,
    but export orchestration does not treat content judgements as technical PDF
    failures. This prevents uncertain claims such as an unsupported meal flag
    from stopping the advisor's work.
    """

    prepared_report = pdf_render_context.client_quality_report
    if prepared_report is None:
        raise RuntimeError("Prepared PDF render context is missing its client quality report.")
    client_quality_report = add_image_quality_issues(
        prepared_report,
        day_images=image_matches,
        image_bank_status=image_bank_status,
    )
    show_review_issue_list(
        "PDF creation can continue. Review the client-output notes before delivery.",
        client_quality_report.issues,
    )
    return client_quality_report


__all__ = [
    "preview_contract_blocks_pdf",
    "row_validation_blocks_pdf",
    "show_client_quality_review",
]
