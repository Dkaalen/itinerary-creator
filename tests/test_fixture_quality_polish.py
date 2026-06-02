from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.day_planner import plan_day
from itinerary_generation.inclusion_transport import transport_line
from itinerary_generation.transport import get_transport_route_phrase


def test_arctic_whale_watching_description_is_not_reykjavik_fallback():
    row = {
        "day": "Day 9",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Alta",
        "title": "Whale Watching & Arctic Wildlife Safari by RIB Boat",
        "original_title": "Whale Watching & Arctic Wildlife Safari by RIB Boat",
        "details": "Alta: Whale Watching & Arctic Wildlife Safari by RIB Boat - Includes: RIB boat, guide",
        "includes": ["RIB boat", "guide"],
    }

    block = canonical_activity_block(row)

    assert block.title == "Whale Watching & Arctic Wildlife Safari"
    assert "Arctic waters" in block.description
    assert "Reykjavík" not in block.description
    assert "Icelandic coast" not in block.description


def test_travel_day_title_prefers_main_coach_over_local_self_transfer():
    rows = [
        {
            "day": "Day 8",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Tromsø",
            "title": "Self transfer from your hotel to the bus station",
            "details": "Tromsø: Self transfer from your hotel to the bus station",
        },
        {
            "day": "Day 8",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Alta",
            "title": "Panoramic Coach Transfer from Tromsø to Alta",
            "details": "Panoramic Coach Transfer from Tromsø to Alta - Time: 10:00 am - 5:00 pm",
        },
    ]

    assert plan_day(rows).title == "Panoramic Coach Transfer from Tromsø to Alta"


def test_private_transfer_inclusion_keeps_city_and_date_context():
    row = {
        "day": "Day 19",
        "type": "Transfer",
        "effective_type": "Transfer",
        "city": "Oslo",
        "title": "Private transfer from your hotel to Oslo Airport",
        "details": "Oslo: Private transfer from your hotel to Oslo Airport",
        "start_date": "2026-10-19",
    }

    assert transport_line(row) == "Oslo - 19th of October\nPrivate transfer from your hotel to Oslo Airport."


def test_norway_in_a_nutshell_explicit_destination_beats_first_internal_leg():
    row = {
        "day": "Day 10",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Oslo",
        "title": "Norway in a Nutshell to Bergen",
        "details": "Oslo: Norway in a Nutshell to Bergen - Route: Oslo to Myrdal by train, Myrdal to Flåm by Flåmsbanen, Flåm to Gudvangen by fjord cruise, Gudvangen to Voss by coach, Voss to Bergen by train",
    }

    assert get_transport_route_phrase(row) == "Norway in a Nutshell to Bergen"
