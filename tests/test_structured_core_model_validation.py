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
