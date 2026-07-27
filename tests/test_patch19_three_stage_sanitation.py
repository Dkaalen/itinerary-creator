from __future__ import annotations

from copy import deepcopy

import pytest

from app_modules.itinerary_render_context import build_itinerary_render_context
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.workbook_export_plan import build_workbook_export_plan
from itinerary_generation.client_output_quality_gate import evaluate_prepared_client_output_quality
from itinerary_generation.client_quality_text import render_document_text
from itinerary_generation.editable_draft import normalise_editable_draft
from itinerary_domain.field_sanitation import (
    CustomerField,
    contains_customer_copy_violation,
    contains_price_or_currency,
    sanitize_customer_field,
    sanitize_customer_html,
)
from itinerary_generation.final_document_sanitation import sanitize_prepared_render_document
from itinerary_generation.render_model import (
    RenderBlock,
    RenderCover,
    RenderDay,
    RenderDocument,
    RenderFinalPage,
    RenderFinalSection,
    RenderMetaLine,
    RenderSection,
    RenderSummary,
)
from shared.source_text_cleanup import clean_supplier_source_text


class _ContinuityStub:
    findings: tuple = ()

    def day_state(self, _day_id: str):
        return None

    def __deepcopy__(self, _memo):
        return self


def test_supplier_cleanup_is_source_safe_and_idempotent() -> None:
    source = (
        "Supplier note: internal only\n"
        "Aurora Hunt by eLyngen\n"
        "3/4-star hotel\n"
        "Departure 10:00 AM - 1:30 PM\n"
        "Flåm - Egilsstaðir - Kittilä"
    )

    cleaned = clean_supplier_source_text(source)

    assert cleaned == (
        "Aurora Hunt by eLyngen\n"
        "3/4-star hotel\n"
        "Departure 10:00 AM - 1:30 PM\n"
        "Flåm - Egilsstaðir - Kittilä"
    )
    assert "Northern Lights" not in cleaned
    assert clean_supplier_source_text(cleaned) == cleaned


@pytest.mark.parametrize(
    ("field", "source", "expected"),
    (
        (CustomerField.DESCRIPTION, "Book here: https://supplier.invalid/book?id=ABC", ""),
        (CustomerField.DESCRIPTION, "Details //supplier.invalid/path for guests", "Details for guests"),
        (CustomerField.DESCRIPTION, "Contact guide@example.com for help", "Contact for help"),
        (CustomerField.DESCRIPTION, "Telephone: +47 123 45 678", ""),
        (CustomerField.DESCRIPTION, "Call 123 45 678", ""),
        (CustomerField.DESCRIPTION, "Supplier code: ABC-123", ""),
        (CustomerField.DESCRIPTION, "Commission: 15%", ""),
        (CustomerField.DESCRIPTION, "Entrance NOK 500 per person", "Entrance"),
        (CustomerField.DESCRIPTION, "Enjoy Aurora. Supplier note: call 123 45 678", "Enjoy Aurora"),
        (CustomerField.DESCRIPTION, "Travel date 2026-09-15", "Travel date 2026-09-15"),
        (CustomerField.DESCRIPTION, "Season 2026 - 2027", "Season 2026 - 2027"),
        (CustomerField.TIME, "10:00 AM - 1:30 PM", "10:00 AM - 1:30 PM"),
        (
            CustomerField.MEETING_POINT,
            "Meeting point: Scandic Ishavshotel, Tromsø at 18:30",
            "Meeting point: Scandic Ishavshotel, Tromsø at 18:30",
        ),
        (
            CustomerField.TITLE,
            "Aurora Hunt by eLyngen at a 3/4-star hotel",
            "Aurora Hunt by eLyngen at a 3/4-star hotel",
        ),
        (
            CustomerField.LOCATION,
            "Flåm – Egilsstaðir – Kittilä – Rovaniemi",
            "Flåm – Egilsstaðir – Kittilä – Rovaniemi",
        ),
        (
            CustomerField.DESCRIPTION,
            "Sámi culture, Þingvellir and Jökulsárlón — déjà vu",
            "Sámi culture, Þingvellir and Jökulsárlón — déjà vu",
        ),
        (CustomerField.DESCRIPTION, "Route: Route: Oslo!!!", "Route: Oslo!"),
    ),
)
def test_field_sanitation_respects_field_semantics(
    field: CustomerField,
    source: str,
    expected: str,
) -> None:
    cleaned = sanitize_customer_field(source, field)

    assert cleaned == expected
    assert sanitize_customer_field(cleaned, field) == cleaned


def test_internal_url_and_note_fields_are_preserved() -> None:
    source_url = "https://supplier.invalid/book?id=ABC"
    internal_note = "Call +47 123 45 678; commission 15%; supplier code ABC-123"

    assert sanitize_customer_field(source_url, CustomerField.URL_METADATA) == source_url
    assert sanitize_customer_field(internal_note, CustomerField.INTERNAL_NOTE) == internal_note


@pytest.mark.parametrize(
    "source",
    (
        '<p onclick="alert(1)"><a href="https://supplier.invalid">Aurora</a></p>',
        '<style>.leak{display:block}</style><p data-source-row-ids="row-1">Safe</p>',
        '<script>alert(1)</script><p>Safe</p>',
        '<script>alert(1)<p>Unsafe tail',
        '<img src="//supplier.invalid/image.jpg" onerror="alert(1)"><p>Safe</p>',
        '<p style="background:url(//supplier.invalid/x)">Safe</p>',
    ),
)
def test_customer_html_removes_unsafe_blocks_urls_and_attributes(source: str) -> None:
    cleaned = sanitize_customer_html(source, CustomerField.DESCRIPTION)
    lower = cleaned.casefold()

    assert "script" not in lower
    assert "style=" not in lower
    assert "onclick" not in lower
    assert "onerror" not in lower
    assert "href=" not in lower
    assert "src=" not in lower
    assert "supplier.invalid" not in lower
    assert sanitize_customer_html(cleaned, CustomerField.DESCRIPTION) == cleaned


def test_customer_html_preserves_safe_markup_and_source_identity() -> None:
    source = '<section class="final" data-source-row-ids="row-1,row-2"><strong>Aurora in Flåm</strong></section>'

    cleaned = sanitize_customer_html(source, CustomerField.DESCRIPTION)

    assert cleaned == source


def _leaky_render_document() -> tuple[RenderDocument, object]:
    continuity = _ContinuityStub()
    return (
        RenderDocument(
            title="Aurora Escape | URL: https://supplier.invalid/book",
            subtitle="Supplier note: internal only",
            route="Flåm – Tromsø",
            warnings=["Internal diagnostic URL https://supplier.invalid/diagnostic"],
            labels={"internal_url": "https://supplier.invalid/labels"},
            hidden_page_ids=["day-day-2"],
            page_order=["cover", "summary", "day-day-1"],
            continuity_report=continuity,
            cover=RenderCover(
                title="Aurora Escape",
                subtitle="Commission: 15%",
                dates="2026-09-15 - 2026-09-20",
                route="Flåm – Tromsø",
                background_path="https://supplier.invalid/internal-cover.jpg",
                season="Winter 2026-2027",
            ),
            summary=RenderSummary(
                trip_glance=[RenderMetaLine("Contact", "guide@example.com")],
                journey_arc=[{"place": "Flåm", "experience": "Aurora!!!"}],
                background_path="https://supplier.invalid/internal-summary.jpg",
            ),
            days=[
                RenderDay(
                    day="Day 1",
                    number="1",
                    city="Flåm",
                    title="Aurora by eLyngen",
                    intro="Enjoy the fjord. Supplier note: do not publish",
                    date="2026-09-15",
                    source_row_ids=["row-1"],
                    warnings=["internal warning"],
                    labels={"source_url": "https://supplier.invalid/row-1"},
                    blocks=[
                        RenderBlock(
                            kind="activity",
                            row_id="row-1",
                            title="3/4-star Aurora Experience",
                            meta=[
                                RenderMetaLine("Time", "10:00 AM - 1:30 PM"),
                                RenderMetaLine("Meeting point", "Harbour, Tromsø"),
                                RenderMetaLine("Supplier URL", "https://supplier.invalid/activity"),
                            ],
                            includes=["Guide", "Entrance EUR 50 per person"],
                            description="Contact guide@example.com or call 123 45 678.",
                            content_html=(
                                '<section data-source-row-ids="row-1" onclick="bad()">'
                                '<script>alert(1)</script><a href="//supplier.invalid">Aurora</a>'
                                "</section>"
                            ),
                            source_row_ids=["row-1"],
                            warnings=["internal block warning"],
                            labels={"source_url": "https://supplier.invalid/activity"},
                        )
                    ],
                )
            ],
            final_sections=[
                RenderFinalSection(
                    "whats_included",
                    "What’s included",
                    pages=[
                        RenderFinalPage(
                            sections=[RenderSection("Activities", ["Aurora tour", "URL: https://supplier.invalid"])],
                            content_html='<ul data-source-row-ids="row-1"><li>Guide</li><script>bad()</script></ul>',
                        )
                    ],
                    metadata={
                        "source_url": "https://supplier.invalid/internal",
                        "source_workbook": "Calculation-template-Inputs-fixed-outline-restored.xlsx",
                        "source_worksheet": "Activities",
                        "source_row": 19,
                    },
                )
            ],
        ),
        continuity,
    )


def test_final_document_sanitation_is_single_contract_safe_and_idempotent() -> None:
    document, continuity = _leaky_render_document()
    preserved = {
        "warnings": deepcopy(document.warnings),
        "labels": deepcopy(document.labels),
        "hidden_page_ids": deepcopy(document.hidden_page_ids),
        "page_order": deepcopy(document.page_order),
        "metadata": deepcopy(document.final_sections[0].metadata),
        "background_path": document.cover.background_path,
    }

    returned = sanitize_prepared_render_document(document)
    once = deepcopy(document)
    sanitize_prepared_render_document(document)

    assert returned is document
    assert document == once
    assert document.continuity_report is continuity
    assert document.warnings == preserved["warnings"]
    assert document.labels == preserved["labels"]
    assert document.hidden_page_ids == preserved["hidden_page_ids"]
    assert document.page_order == preserved["page_order"]
    assert document.final_sections[0].metadata == preserved["metadata"]
    assert document.cover.background_path == preserved["background_path"]
    assert document.days[0].source_row_ids == ["row-1"]
    assert document.days[0].blocks[0].source_row_ids == ["row-1"]

    customer_text = render_document_text(document)
    assert "supplier.invalid" not in customer_text
    assert "guide@example.com" not in customer_text
    assert "123 45 678" not in customer_text
    assert "Commission" not in customer_text
    assert "EUR 50" not in customer_text
    assert "Aurora" in customer_text
    assert "eLyngen" in customer_text
    assert "3/4-star" in customer_text
    assert "2026-09-15" in customer_text
    assert "10:00 AM - 1:30 PM" in customer_text
    assert not contains_customer_copy_violation(customer_text)
    assert not contains_price_or_currency(customer_text)


def test_quality_audits_sanitized_document_without_mutating_it() -> None:
    document, _ = _leaky_render_document()
    sanitize_prepared_render_document(document)
    before = deepcopy(document)

    report = evaluate_prepared_client_output_quality(document)

    assert document == before
    assert "customer_copy_sanitation_bypass" not in {issue.code for issue in report.issues}
    assert "client_price_or_currency_leak" not in {issue.code for issue in report.issues}


def test_render_context_projects_one_sanitized_editor_document_to_preview_and_pdf() -> None:
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Tromsø",
            "title": "Aurora by eLyngen",
            "details": "Meeting point Tromsø harbour at 18:30",
            "commercial_status": "included",
            "row_id": "row-1",
        }
    ]
    draft = normalise_editable_draft(
        {
            "document_pages": [
                {
                    "page_id": "manual-1",
                    "page_type": "manual",
                    "title": "Custom Aurora note",
                    "sort_order": 99,
                    "manual_blocks": [
                        {
                            "block_id": "manual-1__main",
                            "block_type": "manual_text",
                            "editable_fields": {
                                "content_html": (
                                    '<div data-source-row-ids="row-1">Safe note '
                                    '<a href="https://supplier.invalid">book</a>'
                                    '<script>alert(1)</script></div>'
                                )
                            },
                        }
                    ],
                }
            ]
        }
    )

    context = build_itinerary_render_context(
        rows,
        {"Day 1": rows},
        {"days": {}, "editor_draft": draft},
    )

    assert context.render_document is not context.editor_render_document
    assert context.render_document == context.editor_render_document
    preview_manual = next(item for item in context.render_document.final_sections if item.section_id == "manual-1")
    editor_manual = next(item for item in context.editor_render_document.final_sections if item.section_id == "manual-1")
    preview_html = preview_manual.pages[0].content_html
    editor_html = editor_manual.pages[0].content_html
    assert preview_html == editor_html
    assert "supplier.invalid" not in preview_html
    assert "script" not in preview_html.casefold()
    assert 'data-source-row-ids="row-1"' in preview_html
    assert context.client_quality_report is not None
    assert "customer_copy_sanitation_bypass" not in {issue.code for issue in context.client_quality_report.issues}


def test_excel_export_keeps_internal_source_url_and_provenance_outside_customer_copy() -> None:
    row = CalculatorRow(
        row_id="1",
        day="Day 1",
        type="Activity",
        travel_element="Aurora by eLyngen",
        url="https://supplier.invalid/activity/19",
        gross_price_per_unit=100,
        units=1,
        library_id="activity-row-19",
        source_workbook="Calculation-template-Inputs-fixed-outline-restored.xlsx",
        source_sheet="Activities",
        source_row=19,
    )

    plan = build_workbook_export_plan(CalculatorState(rows=(row,)))

    assert plan.source_provenance[0].source_url == "https://supplier.invalid/activity/19"
    assert plan.source_provenance[0].source_workbook == "Calculation-template-Inputs-fixed-outline-restored.xlsx"
    assert plan.source_provenance[0].source_sheet == "Activities"
    assert plan.source_provenance[0].source_row == 19
    assert sanitize_customer_field(row.travel_element, CustomerField.TITLE) == "Aurora by eLyngen"
