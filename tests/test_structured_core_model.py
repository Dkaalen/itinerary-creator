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
        ("generated-row-0",),
        ("generated-row-1",),
        ("generated-row-2",),
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


def test_structured_activity_inclusion_titles_render_as_separate_bullets():
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
    assert '<li>Round-trip viewpoint ticket in Tromsø - 2nd of November</li>' in html
    assert 'Fjellheisen Cable Car - 2nd of November' not in html
    assert '<li>Oslo Walking Tour - 5th of November</li>' in html


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


def test_structured_inclusion_synthetic_grouped_rows_do_not_get_fake_source_ids():
    source_rows = [
        {
            "row_id": "real-activity",
            "day": "Day 1",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-01",
            "city": "Tromso",
            "title": "Northern Lights Chase",
        }
    ]
    synthetic_hotel = {
        "day": "Day 1",
        "type": "Hotel",
        "source_type": "Hotel",
        "effective_type": "Hotel",
        "start_date": "2026-11-01",
        "city": "Tromso",
        "title": "Synthetic Tour Hotel",
        "hotel_name": "Synthetic Tour Hotel",
        "hotel_nights": "1",
    }

    document = build_itinerary_document(source_rows, {"Day 1": [source_rows[0], synthetic_hotel]})
    accommodation = next(section for section in document.inclusions if section.section_id == "accommodation")

    assert accommodation.items[0].source_row_ids == ()
    assert not any(warning.code == "structured_list_item_missing_source_row" for warning in document.warnings)


def test_structured_document_warns_when_activity_title_loses_source_signal():
    rows = [
        {
            "row_id": "fjord-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Munch Museum admission ticket",
            "original_title": "Tromsø: Photo Tour to Arctic Landscapes and Fjords",
            "details": "Scenic fjord safari by minivan vehicle with professional photo guides.",
            "commercial_status": "included",
        }
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    warning_codes = {warning.code for warning in document.warnings}

    assert "activity_source_signal_missing_from_title" in warning_codes
    assert any("fjord" in warning.message.lower() for warning in document.warnings)


def test_structured_document_keeps_legitimate_cleaned_activity_title_clear():
    rows = [
        {
            "row_id": "oslo-row",
            "day": "Day 10",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-05",
            "city": "Oslo",
            "title": "Oslo Walking Tour",
            "original_title": "Oslo : Essential Oslo, City Center Guided Walking Tour | 10 AM | 2 Hrs",
            "details": "Experience the beauty of the Norwegian capital on foot with this walking tour.",
            "commercial_status": "included",
        }
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))

    assert not any(warning.code == "activity_title_not_supported_by_source" for warning in document.warnings)
    assert not any(warning.code == "activity_source_signal_missing_from_title" for warning in document.warnings)


def test_visual_editor_payload_surfaces_structured_model_warnings():
    rows = [
        {
            "row_id": "fjord-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Munch Museum admission ticket",
            "original_title": "Tromsø: Photo Tour to Arctic Landscapes and Fjords",
            "details": "Scenic fjord safari by minivan vehicle with professional photo guides.",
            "commercial_status": "included",
        }
    ]

    payload = build_visual_editor_payload(rows, group_rows_by_day(rows), {"days": {}, "pictures_added": False})

    assert any(warning["code"] == "activity_source_signal_missing_from_title" for warning in payload["model_warnings"])
    assert any(warning["code"] == "activity_source_signal_missing_from_title" for warning in payload["client_output_warnings"])


def test_structured_validation_warns_when_included_activity_has_no_inclusion_coverage():
    from itinerary_generation.structured_model import DayDocument, DocumentItem, ItineraryDocument, SourceRowRef
    from itinerary_generation.structured_validation import validate_itinerary_document

    document = ItineraryDocument(
        source_rows=(
            SourceRowRef(
                row_id="fjord-row",
                line_number=1,
                day="Day 7",
                source_type="Activity",
                effective_type="Activity",
                raw_text="Tromsø: Photo Tour to Arctic Landscapes and Fjords",
                title="Tromsø: Photo Tour to Arctic Landscapes and Fjords",
                commercial_status="included",
            ),
        ),
        days=(DayDocument(day="Day 7", number="7", item_ids=("fjord-row",), source_row_ids=("fjord-row",)),),
        items=(
            DocumentItem(
                item_id="fjord-row",
                kind="activity",
                day="Day 7",
                date="2026-11-02",
                destination="Tromso",
                title="Tromsø: Photo Tour to Arctic Landscapes and Fjords",
                source_row_ids=("fjord-row",),
                commercial_status="included",
            ),
        ),
        inclusions=(),
    )

    warnings = validate_itinerary_document(document)

    assert any(warning.code == "included_item_missing_inclusion_coverage" for warning in warnings)


def test_structured_validation_keeps_weak_viewpoint_label_generic_and_warns():
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
            "details": "",
            "commercial_status": "included",
        }
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    codes = {warning.code for warning in document.warnings}

    assert "ambiguous_activity_title" in codes
    assert "inclusion_label_inferred_from_weak_source" not in codes
    inclusion_labels = [item.label for section in document.inclusions for item in section.items]
    assert any("Round-trip viewpoint ticket in Tromsø" in label for label in inclusion_labels)
    assert all("Fjellheisen" not in label for label in inclusion_labels)


def test_structured_validation_warns_when_activity_inclusion_loses_fjord_signal():
    rows = [
        {
            "row_id": "fjord-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Munch Museum admission ticket",
            "original_title": "Tromsø: Photo Tour to Arctic Landscapes and Fjords",
            "details": "Scenic fjord safari by minivan vehicle with professional photo guides.",
            "commercial_status": "included",
        }
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    codes = {warning.code for warning in document.warnings}

    assert "activity_source_signal_missing_from_title" in codes
    assert "inclusion_source_signal_missing_from_label" in codes


def test_structured_activity_signal_guard_does_not_treat_generic_ticket_as_museum():
    rows = [
        {
            "row_id": "ticket-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Tromso",
            "title": "Fjellheisen Cable Car",
            "original_title": "Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.",
            "commercial_status": "included",
        }
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))

    assert not any(
        warning.code == "activity_source_signal_missing_from_title" and "museum" in warning.message.lower()
        for warning in document.warnings
    )



def test_structured_exclusion_items_keep_source_ids_for_self_arranged_and_activity_costs():
    rows = [
        {
            "row_id": "flight-row",
            "day": "Day 6",
            "type": "Flight",
            "source_type": "Transfer",
            "effective_type": "Flight",
            "start_date": "2026-11-01",
            "city": "Tromso",
            "title": "Flight Ivalo to Tromso | self arranged, price not included",
            "commercial_status": "self_arranged",
        },
        {
            "row_id": "activity-row",
            "day": "Day 7",
            "type": "Activity",
            "source_type": "Activity",
            "effective_type": "Activity",
            "start_date": "2026-11-02",
            "city": "Bergen",
            "title": "Bergen Walking Tour",
            "details": "Not included: Entrance fees, Food and drinks are excluded",
            "commercial_status": "included",
        },
    ]

    document = build_itinerary_document(rows, group_rows_by_day(rows))
    exclusion_sources = {
        row_id
        for section in document.exclusions
        for item in section.items
        for row_id in item.source_row_ids
    }

    assert "flight-row" in exclusion_sources
    assert "activity-row" in exclusion_sources
    assert not any(warning.code == "commercial_row_missing_exclusion_coverage" for warning in document.warnings)


def test_structured_validation_warns_when_commercial_row_loses_exclusion_source_coverage():
    from itinerary_generation.structured_model import ItineraryDocument, SourceRowRef, StructuredListItem, StructuredListSection
    from itinerary_generation.structured_validation import validate_itinerary_document

    document = ItineraryDocument(
        source_rows=(
            SourceRowRef(
                row_id="self-flight-row",
                line_number=1,
                day="Day 6",
                source_type="Transfer",
                effective_type="Flight",
                raw_text="Flight Ivalo to Tromso | self arranged, price not included",
                title="Flight Ivalo to Tromso",
                commercial_status="self_arranged",
            ),
        ),
        exclusions=(
            StructuredListSection(
                section_id="general",
                title="General exclusions",
                items=(StructuredListItem(label="International flights unless specifically listed"),),
            ),
        ),
    )

    warnings = validate_itinerary_document(document)

    assert any(warning.code == "commercial_row_missing_exclusion_coverage" for warning in warnings)
