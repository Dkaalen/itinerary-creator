import sys
import types
from shared.source_rows import source_row_id

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

from app_modules.itinerary_html import build_itinerary_html
from app_modules.parse_workflow import parse_and_normalize_itinerary
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.exclusion_sections import create_structured_whats_not_included
from itinerary_generation.structured_builder import build_itinerary_document
from visual_editor_component.editor_workflow import apply_visual_editor_result, build_visual_editor_payload


def _rows(raw: str):
    return parse_and_normalize_itinerary(raw)


def test_structured_document_preserves_one_activity_per_source_row():
    raw = """
Day 1	Activity	02/11/2026								Tromso	Tromsø: Photo Tour to Arctic Landscapes and Fjords | 11 AM | 5 Hrs | Scenic fjord safari by minivan vehicle
Day 1	Activity	02/11/2026								Tromso	Tromsø: Munch Museum admission ticket | 13:00 | Tickets included
"""
    rows = _rows(raw)
    document = build_itinerary_document(rows, group_rows_by_day(rows))
    activities = document.items_by_kind("activity")

    assert len(activities) == 2
    assert len({activity.item_id for activity in activities}) == 2
    assert any("Fjords" in activity.title for activity in activities)
    assert any("Munch Museum" in activity.title for activity in activities)
    assert all(len(activity.source_row_ids) == 1 for activity in activities)


def test_structured_document_flags_ambiguous_round_trip_ticket_title():
    raw = """
Day 7	Activity	02/11/2026								Tromso	Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.
"""
    rows = _rows(raw)
    document = build_itinerary_document(rows, group_rows_by_day(rows))

    assert any(warning.code == "ambiguous_activity_title" for warning in document.warnings)
    assert document.items_by_kind("activity")[0].confidence < 1.0


def test_structured_exclusions_are_sections_not_one_flat_paragraph():
    raw = """
Day 1	Transfer	01/11/2026								Tromso	Flight Ivalo to Tromso | self arranged , price not included
Day 2	Activity	02/11/2026								Bergen	Bergen Walking Tour | Not included: Entrance fees, Food and drinks are excluded
"""
    rows = _rows(raw)
    sections = create_structured_whats_not_included(rows)
    def labels(items):
        return [item["label"] if isinstance(item, dict) else item for item in items]

    by_title = {section["title"]: section["items"] for section in sections}

    assert "Self-arranged flights" in by_title
    assert labels(by_title["Self-arranged flights"]) == ["Flight from Ivalo to Tromsø - 1st of November"]
    assert by_title["Self-arranged flights"][0]["source_row_ids"]
    assert "General exclusions" in by_title
    assert all("\n" not in label for section in sections for label in labels(section["items"]))


def test_visual_editor_uses_html_list_for_whats_not_included():
    raw = """
Day 1	Transfer	01/11/2026								Tromso	Flight Ivalo to Tromso | self arranged , price not included
"""
    rows = _rows(raw)
    payload = build_visual_editor_payload(rows, group_rows_by_day(rows), {"days": {}, "pictures_added": False})

    assert "whats_not_included_html" in payload["final_pages"]
    assert "<li>" in payload["final_pages"]["whats_not_included_html"]
    assert "Self-arranged flights" in payload["final_pages"]["whats_not_included_html"]
    assert "whats_not_included_text" in payload["final_pages"]  # legacy project compatibility


def test_saved_whats_not_included_html_controls_preview_without_flattening():
    output_edits = {"days": {}}
    result = {
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {
            "whats_not_included_html": '<ul class="final-list"><li>Edited exclusion</li></ul>',
            "whats_not_included_text": "Edited exclusion",
        },
    }

    assert apply_visual_editor_result(result, output_edits)
    assert output_edits["whats_not_included_html"] == '<ul class="final-list"><li>Edited exclusion</li></ul>'
    assert output_edits["whats_not_included_text"] == ""

    html = build_itinerary_html([], {}, output_edits)
    assert '<ul class="final-list"><li>Edited exclusion</li></ul>' in html


def test_structured_document_links_fallback_row_ids_across_multiple_days():
    rows = [
        {"day": "Day 1", "type": "Activity", "source_type": "Activity", "effective_type": "Activity", "start_date": "01/11/2026", "city": "Helsinki", "title": "Helsinki Walking Tour"},
        {"day": "Day 2", "type": "Activity", "source_type": "Activity", "effective_type": "Activity", "start_date": "02/11/2026", "city": "Tromso", "title": "Tromsø Fjord Cruise"},
        {"day": "Day 3", "type": "Hotel", "source_type": "Hotel", "effective_type": "Hotel", "start_date": "03/11/2026", "city": "Oslo", "title": "Comfort Hotel Børsparken"},
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))

    assert [day.item_ids for day in document.days] == [
        (source_row_id(rows[0]),),
        (source_row_id(rows[1]),),
        (source_row_id(rows[2]),),
    ]
    assert not any(warning.code == "included_items_not_linked_to_day" for warning in document.warnings)


def test_preview_renders_inclusions_and_exclusions_from_structured_document_sections():
    raw = """
Day 1	Transfer	01/11/2026								Tromso	Flight Ivalo to Tromso | self arranged , price not included
Day 2	Activity	02/11/2026								Tromso	Tromsø: Photo Tour to Arctic Landscapes and Fjords | 11 AM | 5 Hrs | Scenic fjord safari by minivan vehicle
"""
    rows = _rows(raw)
    html = build_itinerary_html(rows, group_rows_by_day(rows), {"days": {}, "pictures_added": False})

    assert "What’s included" in html
    assert "What’s not included" in html
    assert "Self-arranged flights" in html
    assert "Flight from Ivalo to Tromsø" in html
    assert "General exclusions" in html
    assert "Scenic fjord safari" in html or "Photo Tour to Arctic Landscapes" in html
    # The not-included page must stay as list HTML, not a single collapsed paragraph.
    not_included_section = html.split("What’s not included", 1)[1]
    assert "<li>" in not_included_section


def test_structured_renderer_keeps_label_and_detail_lines_separate():
    from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
    from ui.inclusion_pages import render_inclusion_sections_inner_html

    html = render_inclusion_sections_inner_html([
        StructuredListSection(
            section_id="activities",
            title="Activities & Experiences",
            items=(
                StructuredListItem(
                    label="Oslo Walking Tour - 5th of November",
                    detail_lines=("Guided city centre walk", "Duration: 2 hours"),
                ),
            ),
        )
    ])

    assert "Oslo Walking Tour - 5th of November" in html
    assert "Guided city centre walk" in html
    assert "Duration: 2 hours" in html
    assert html.index("Oslo Walking Tour") < html.index("Guided city centre walk")


def test_structured_inclusions_keep_source_ids_for_activity_rows():
    rows = [
        {
            "row_id": "fjord-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Tromsø: Photo Tour to Arctic Landscapes and Fjords",
            "details": "Scenic fjord safari by minivan vehicle",
            "includes": ["Professional, English-speaking photo guides", "Scenic fjord safari by minivan vehicle"],
        },
        {
            "row_id": "munch-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Oslo",
            "title": "Munch Museum admission ticket",
            "details": "Admission ticket included",
            "includes": ["Admission ticket included"],
        },
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    activities_section = next(section for section in document.inclusions if section.section_id == "activities")

    assert len(activities_section.items) == 2
    assert {item.source_row_ids for item in activities_section.items} == {("fjord-row",), ("munch-row",)}
    fjord_item = next(item for item in activities_section.items if item.source_row_ids == ("fjord-row",))
    munch_item = next(item for item in activities_section.items if item.source_row_ids == ("munch-row",))
    assert "Fjords" in fjord_item.label
    assert "Munch Museum" not in fjord_item.label
    assert "Munch Museum" in munch_item.label
    assert "Fjord" not in munch_item.label


def test_structured_activity_inclusion_titles_render_as_client_entries_not_loose_bullets():
    rows = [
        {
            "row_id": "fjellheisen-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Fjellheisen Cable Car",
            "original_title": "Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.",
            "details": "Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.",
            "includes": [],
        },
        {
            "row_id": "oslo-row",
            "day": "Day 10",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-05",
            "city": "Oslo",
            "title": "Oslo : Essential Oslo, City Center Guided Walking Tour",
            "details": "Experience the beauty of the Norwegian capital on foot with this walking tour",
            "includes": [],
        },
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    activities_section = next(section for section in document.inclusions if section.section_id == "activities")
    labels = [item.label for item in activities_section.items]
    html = build_itinerary_html(rows, group_rows_by_day(rows), {"days": {}, "pictures_added": False})

    assert labels == ["Round-trip viewpoint ticket in Tromsø - 2nd of November", "Oslo Walking Tour - 5th of November"]
    assert '<div class="body-text strong-line inclusion-entry-title">Round-trip viewpoint ticket in Tromsø - 2nd of November</div>' in html
    assert '<li>Round-trip viewpoint ticket in Tromsø - 2nd of November</li>' not in html
    assert 'Fjellheisen Cable Car - 2nd of November' not in html
    assert '<div class="body-text strong-line inclusion-entry-title">Oslo Walking Tour - 5th of November</div>' in html
    assert '<li>Oslo Walking Tour - 5th of November</li>' not in html


def test_structured_list_source_ids_are_validated():
    from itinerary_generation.structured_model import ItineraryDocument, StructuredListItem, StructuredListSection
    from itinerary_generation.structured_validation import validate_itinerary_document

    document = ItineraryDocument(
        source_rows=(),
        inclusions=(
            StructuredListSection(
                section_id="activities",
                title="Activities & experiences",
                items=(StructuredListItem(label="Ghost activity", source_row_ids=("missing-row",)),),
            ),
        ),
    )

    warnings = validate_itinerary_document(document)

    assert any(warning.code == "structured_list_item_missing_source_row" for warning in warnings)


def test_visual_editor_recovers_collapsed_whats_not_included_list_html():
    output_edits = {"days": {}}
    collapsed_html = (
        "International flights unless specifically listed "
        "Self-arranged flights "
        "Flight from Ivalo to Tromsø - 1st of November "
        "Meals unless specifically stated "
        "Travel insurance"
    )

    result = {
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {"whats_not_included_html": collapsed_html},
    }

    assert apply_visual_editor_result(result, output_edits)
    saved = output_edits["whats_not_included_html"]

    assert '<ul class="final-list">' in saved
    assert saved.count("<li>") >= 5
    assert "<li>International flights unless specifically listed</li>" in saved
    assert "<li>Self-arranged flights</li>" in saved
    assert "<li>Flight from Ivalo to Tromsø - 1st of November</li>" in saved
    assert "<li>Meals unless specifically stated</li>" in saved
    assert "<li>Travel insurance</li>" in saved
