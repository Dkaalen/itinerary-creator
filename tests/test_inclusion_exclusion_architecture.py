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

def test_structured_exclusion_sections_group_specific_commercial_rows():
    from itinerary_generation.exclusion_sections import create_specific_exclusion_sections

    rows = [
        {
            "day": "Day 9",
            "type": "Transfer",
            "effective_type": "Transfer",
            "title": "Flight Tromsø to Bergen",
            "details": "self-arranged cost not included",
            "start_date": "2026-12-31",
            "commercial_status": "self_arranged",
            "commercial_reason": "cost_not_included",
        },
        {
            "day": "Day 13",
            "type": "Transfer",
            "effective_type": "Transfer",
            "title": "Self Transfer Hotel to Airport",
            "details": "Self Transfer Hotel to Airport",
            "start_date": "2027-01-04",
            "commercial_status": "self_arranged",
            "commercial_reason": "self_transfer",
        },
        {
            "day": "Day 5",
            "type": "Activity",
            "effective_type": "Activity",
            "title": "Northern Lights Hunt",
            "details": "Optional add-on Northern Lights Hunt",
            "start_date": "2026-12-27",
            "is_optional": True,
            "commercial_status": "optional",
        },
        {
            "day": "Day 6",
            "type": "Transfer",
            "effective_type": "Transfer",
            "title": "Optional private transfer to the glass igloos",
            "details": "Optional transfer",
            "start_date": "2026-12-28",
            "is_optional": True,
            "commercial_status": "optional",
        },
        {
            "day": "Day 7",
            "type": "Hotel",
            "effective_type": "Hotel",
            "title": "Optional Igloo Upgrade",
            "details": "Optional hotel upgrade",
            "start_date": "2026-12-29",
            "is_optional": True,
            "commercial_status": "optional",
        },
        {
            "day": "Day 8",
            "type": "Transfer",
            "effective_type": "Transfer",
            "title": "Coach transfer",
            "details": "tickets not included",
            "start_date": "2026-12-30",
            "commercial_status": "excluded",
            "commercial_reason": "not_included_marker",
        },
    ]

    sections = create_specific_exclusion_sections(rows)
    assert sections["self_arranged_flights"] == ["Flight from Tromsø to Bergen - 31st of December"]
    assert sections["self_transfers"] == ["Self Transfer Hotel to Airport - 4th of January"]
    assert sections["optional_experiences"] == ["Northern Lights Hunt - 27th of December"]
    assert sections["optional_transfers"] == ["Optional private transfer to the glass igloos - 28th of December"]
    assert sections["optional_hotels"] == ["Optional Igloo Upgrade - 29th of December"]
    assert sections["costs_not_included"] == ["Coach Transfer - 30th of December"]

    text = "\n".join(create_exclusions(rows))
    assert "Self-arranged flights\nFlight from Tromsø to Bergen - 31st of December" in text
    assert "Self transfers\nSelf Transfer Hotel to Airport - 4th of January" in text
    assert "Optional experiences\nNorthern Lights Hunt - 27th of December" in text
    assert "Optional transfers\nOptional private transfer to the glass igloos - 28th of December" in text
    assert "Optional hotels/add-ons\nOptional Igloo Upgrade - 29th of December" in text
    assert "Costs not included\nCoach Transfer - 30th of December" in text


def test_rental_safety_deposit_is_specific_cost_not_raw_rental_pickup():
    from itinerary_generation.exclusion_sections import create_specific_exclusion_sections

    rows = [
        {
            "day": "Day 1",
            "type": "Day Overview",
            "effective_type": "Day Overview",
            "title": "Pick-up Rental vehicle from Office or Airport",
            "details": "Pick-up Rental SUV included automatic full insurance. Not included: Safety deposit",
            "start_date": "2026-07-09",
            "commercial_status": "included",
            "commercial_reason": "default_included",
        }
    ]

    sections = create_specific_exclusion_sections(rows)
    assert sections["costs_not_included"] == ["Rental vehicle safety deposit"]
    text = "\n".join(create_exclusions(rows))
    assert "Rental vehicle safety deposit" in text
    assert "Pick-up Rental vehicle from Office or Airport" not in text

