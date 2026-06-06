import sys
import types

streamlit_stub = sys.modules.get("streamlit") or types.ModuleType("streamlit")
streamlit_stub.session_state = getattr(streamlit_stub, "session_state", {})
streamlit_stub.warning = getattr(streamlit_stub, "warning", lambda *args, **kwargs: None)
streamlit_stub.success = getattr(streamlit_stub, "success", lambda *args, **kwargs: None)
components_stub = sys.modules.get("streamlit.components") or types.ModuleType("streamlit.components")
components_v1_stub = sys.modules.get("streamlit.components.v1") or types.ModuleType("streamlit.components.v1")
components_v1_stub.declare_component = getattr(components_v1_stub, "declare_component", lambda *args, **kwargs: (lambda **component_kwargs: None))
streamlit_stub.components = components_stub
components_stub.v1 = components_v1_stub
sys.modules["streamlit"] = streamlit_stub
sys.modules["streamlit.components"] = components_stub
sys.modules["streamlit.components.v1"] = components_v1_stub

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_html_audit import (
    source_row_ids_in_html,
    validate_source_aware_html_coverage,
)
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
from ui.inclusion_pages import render_inclusion_sections_inner_html
from visual_editor_component.editor_workflow import build_visual_editor_payload


def test_structured_final_page_html_preserves_source_row_ids_on_list_items():
    html = render_inclusion_sections_inner_html([
        StructuredListSection(
            section_id="activities",
            title="Activities & experiences",
            items=(
                StructuredListItem(
                    label="Fjellheisen Cable Car - 2nd of November",
                    source_row_ids=("fjellheisen-row",),
                ),
                StructuredListItem(
                    label="Oslo Walking Tour - 5th of November",
                    source_row_ids=("oslo-walk-row",),
                ),
            ),
        )
    ])

    assert '<div class="body-text strong-line inclusion-entry-title">Fjellheisen Cable Car - 2nd of November</div>' in html
    assert '<li>Fjellheisen Cable Car - 2nd of November</li>' not in html
    assert 'data-source-row-ids="fjellheisen-row"' in html
    assert 'data-source-row-ids="oslo-walk-row"' in html
    assert source_row_ids_in_html(html) == ("fjellheisen-row", "oslo-walk-row")


def test_structured_final_page_html_preserves_source_row_ids_on_multiline_entries():
    html = render_inclusion_sections_inner_html([
        StructuredListSection(
            section_id="activities",
            title="Activities & experiences",
            items=(
                StructuredListItem(
                    label="Tromsø Fjord Photo Tour - 2nd of November",
                    detail_lines=("Scenic fjord safari by minivan",),
                    source_row_ids=("fjord-row",),
                ),
            ),
        )
    ])

    assert 'Tromsø Fjord Photo Tour - 2nd of November' in html
    assert 'data-source-row-ids="fjord-row"' in html
    assert source_row_ids_in_html(html) == ("fjord-row",)


def test_source_aware_html_audit_warns_when_editor_drops_structured_item_identity():
    sections = [
        StructuredListSection(
            section_id="activities",
            title="Activities & experiences",
            items=(
                StructuredListItem(label="Fjord Photo Tour", source_row_ids=("fjord-row",)),
                StructuredListItem(label="Munch Museum", source_row_ids=("munch-row",)),
            ),
        )
    ]

    warnings = validate_source_aware_html_coverage(
        html_fragments='<ul><li data-source-row-ids="fjord-row">Fjord Photo Tour</li></ul>',
        sections=sections,
        page_name="What's included",
        warning_code="edited_inclusions_missing_source_identity",
    )

    assert len(warnings) == 1
    assert warnings[0].code == "edited_inclusions_missing_source_identity"
    assert warnings[0].source_row_ids == ("munch-row",)


def test_visual_editor_payload_warns_if_saved_exclusion_html_loses_source_identity():
    rows = [
        {
            "row_id": "self-flight-row",
            "day": "Day 1",
            "type": "Flight",
            "source_type": "Flight",
            "effective_type": "Flight",
            "start_date": "2026-11-01",
            "city": "Tromso",
            "title": "Flight Ivalo to Tromso | self arranged, price not included",
            "details": "Flight Ivalo to Tromso | self arranged, price not included",
            "commercial_status": "self_arranged",
            "commercial_reason": "self_arranged",
        }
    ]
    grouped = group_rows_by_day(rows)

    payload = build_visual_editor_payload(
        rows,
        grouped,
        {
            "days": {},
            "pictures_added": False,
            "whats_not_included_html": '<ul class="final-list"><li>Travel insurance</li></ul>',
        },
    )

    assert any(
        warning["code"] == "edited_exclusions_missing_source_identity"
        and "self-flight-row" in warning["source_row_ids"]
        for warning in payload["model_warnings"]
    )
    assert any(
        warning["code"] == "edited_exclusions_missing_source_identity"
        for warning in payload["client_output_warnings"]
    )
