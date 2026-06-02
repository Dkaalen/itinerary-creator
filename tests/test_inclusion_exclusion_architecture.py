from itinerary_generation.exclusion_sections import create_whats_not_included as create_exclusions
from itinerary_generation.inclusion_flat import create_whats_included
from itinerary_generation.inclusions import create_whats_not_included as create_exclusions_facade
from itinerary_generation.common import group_rows_by_day


def test_inclusion_facade_preserves_exclusion_api():
    rows = [
        {
            "day": "Day 1",
            "type": "Transfer",
            "effective_type": "Transfer",
            "title": "Self Transfer Hotel to Airport",
            "details": "Self Transfer Hotel to Airport",
            "start_date": "2026-08-08",
            "commercial_status": "self_arranged",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "title": "Second Walrus Safari Boat Tour",
            "details": "Optional add-on walrus safari",
            "start_date": "2026-08-09",
            "is_optional": True,
            "commercial_status": "optional",
        },
    ]

    direct = create_exclusions(rows)
    facade = create_exclusions_facade(rows)

    assert facade == direct
    text = "\n".join(facade)
    assert "Self-arranged flights or transport" in text
    assert "Self Transfer Hotel to Airport" in text
    assert "Optional experiences unless specifically confirmed" in text
    assert "Second Walrus Safari Boat Tour" in text


def test_legacy_flat_inclusion_builder_stays_in_inclusion_module_boundary():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "title": "Hotel Arthur",
            "details": "Hotel Arthur, 2xNight, 1xStandard Double Room, Incl Breakfast",
            "hotel_nights": "2",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "title": "Oslo Walking Tour",
            "details": "Guided walking tour",
        },
    ]

    included = create_whats_included(rows, group_rows_by_day(rows))

    assert "2 nights as specified" in included
    assert "Accommodation as listed in the itinerary" in included
    assert "Breakfast included where specified" in included
    assert "Oslo Walking Tour" in included
