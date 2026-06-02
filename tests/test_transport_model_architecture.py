from itinerary_generation.common import get_row_type
from itinerary_generation.transport import (
    TRANSPORT_CORE_FIELDS,
    get_transport_row_context,
    get_transport_source_text,
    has_local_transfer_marker,
    is_transport_like_row,
)
from itinerary_generation.transport_routes import _transport_source_text


def test_transport_source_text_has_single_compatibility_path():
    row = {
        "title": "Flight to Bergen",
        "details": "Time: 10:00 - 11:00",
        "original_title": "Flight Oslo to Bergen | tickets included",
    }

    assert get_transport_source_text(row) == _transport_source_text(row)
    assert "Flight to Bergen" in get_transport_source_text(row)
    assert "tickets included" in get_transport_source_text(row)


def test_transport_context_carries_row_type_and_search_text():
    row = {"type": "Transfer", "title": "Private Airport to Hotel"}

    context = get_transport_row_context(row)

    assert context.row_type == get_row_type(row)
    assert context.source_text == "Private Airport to Hotel"
    assert context.search_text == "private airport to hotel"


def test_local_transfer_marker_centralizes_private_and_self_transfer_checks():
    assert has_local_transfer_marker("Private Airport to Hotel")
    assert has_local_transfer_marker("Self transfer from hotel to station")
    assert has_local_transfer_marker("Transfer to your accommodation")
    assert not has_local_transfer_marker("Panoramic coach transfer from Rovaniemi to Tromsø")


def test_transport_like_rows_match_travel_arrangement_scope():
    assert is_transport_like_row({"type": "Transfer"})
    assert is_transport_like_row({"type": "Flight"})
    assert not is_transport_like_row({"type": "Drive"})
    assert is_transport_like_row({"type": "Drive"}, include_drive=True)
    assert not is_transport_like_row({"type": "Activity"}, include_drive=True)


def test_transport_core_fields_preserve_legacy_title_details_checks():
    row = {
        "title": "Private Airport to Hotel",
        "details": "included transfer",
        "original_title": "Original row mentioning optional ferry",
    }

    assert get_transport_source_text(row, TRANSPORT_CORE_FIELDS) == "Private Airport to Hotel included transfer"

