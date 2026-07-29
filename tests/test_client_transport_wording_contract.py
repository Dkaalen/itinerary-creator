from __future__ import annotations

from itinerary_parser import parse_itinerary
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.transport_domain.client_wording import (
    build_client_transport_wording,
    build_day_client_transport_wording,
)
from itinerary_generation.transport_domain.inclusions import transport_line
from itinerary_generation.transport_domain.render_sequences import get_travel_sequence_line
from itinerary_generation.transport_domain.titles import get_primary_transport_title, get_transport_route_phrase


def _row(raw: str) -> dict:
    rows = parse_itinerary(raw)
    assert len(rows) == 1
    return rows[0]


def test_client_transport_wording_repairs_route_truth_before_copy() -> None:
    fjord = _row(
        "Day 6\tCruise\t08.09.2026\t\tGudvangen: Nærøyfjord Cruise to Flåm - "
        "Time: 12:00 pm - 2:00 pm - Includes: Tickets"
    )
    flight = _row(
        "Day 3\tFlight\t03.01.2027\t\tTromsø: Flight to Bergen - "
        "Time: 11:15 am - 1:20 pm - Includes: Tickets, Luggage (1 x 23 kg)"
    )
    arrival = _row("Day 13\tCruise\t13.10.2026\t\tCruise: Arrival to Bergen at 2:45 pm")

    fjord_wording = build_client_transport_wording(fjord)
    flight_wording = build_client_transport_wording(flight)
    arrival_wording = build_client_transport_wording(arrival)

    assert (fjord_wording.origin, fjord_wording.destination) == ("Gudvangen", "Flåm")
    assert fjord_wording.arrangement_title == "Nærøyfjord Cruise from Gudvangen to Flåm"
    assert fjord_wording.day_title == "Cruise to Flåm"

    assert (flight_wording.origin, flight_wording.destination) == ("Tromsø", "Bergen")
    assert flight_wording.arrangement_title == "Flight from Tromsø to Bergen"
    assert flight_wording.day_title == "Flight to Bergen"

    assert arrival_wording.destination == "Bergen"
    assert arrival_wording.arrangement_title == "Cruise arrival to Bergen"
    assert not arrival_wording.arrangement_title.endswith((" at", " on", " to"))


def test_transport_titles_arrangements_and_inclusions_share_one_wording_contract() -> None:
    row = _row(
        "Day 3\tFlight\t03.01.2027\t\tTromsø: Flight to Bergen - "
        "Time: 11:15 am - 1:20 pm - Includes: Tickets, Luggage (1 x 23 kg)"
    )
    wording = build_client_transport_wording(row)

    assert get_transport_route_phrase(row) == wording.arrangement_title
    assert get_travel_sequence_line(row) == wording.arrangement_title
    assert transport_line(row).splitlines()[0] == wording.inclusion_title
    assert get_primary_transport_title([row]) == wording.day_title


def test_commercial_status_is_part_of_transport_wording_contract() -> None:
    self_arranged = _row(
        "Day 1\tFlight\t01.01.2027\t\tOslo: Flight Oslo to Tromsø self arranged cost not included"
    )
    included = _row(
        "Day 2\tFlight\t02.01.2027\t\tTromsø: Flight to Bergen - Includes: Tickets"
    )

    self_arranged_wording = build_client_transport_wording(self_arranged)
    included_wording = build_client_transport_wording(included)

    assert self_arranged_wording.commercial_status == "self_arranged"
    assert self_arranged_wording.commercial_title == "Self-arranged flight from Oslo to Tromsø (not included)"
    assert included_wording.commercial_status == "included"
    assert included_wording.commercial_title == "Flight from Tromsø to Bergen"


def test_service_names_cannot_become_route_origins_or_day_intro_copy() -> None:
    coach = _row(
        "Day 8\tTransport\t08.01.2027\t\tRovaniemi: Overnight Arctic Coach transfer "
        "on the Northern Lights Express to Tromsø - Time: TBD - Includes: Tickets"
    )
    rail = _row(
        "Day 8\tTrain\t08.09.2026\t\tBergen: Train transfer on the Bergen Line and "
        "Flåm Railway with connection in Myrdal to Flåm - Time: TBD - Includes: Tickets"
    )

    coach_wording = build_client_transport_wording(coach)
    rail_wording = build_client_transport_wording(rail)

    assert (coach_wording.origin, coach_wording.destination) == ("Rovaniemi", "Tromsø")
    assert coach_wording.travel_phrase == "Travel overnight from Rovaniemi to Tromsø by coach"
    assert "Northern Lights Express" not in coach_wording.origin

    assert (rail_wording.origin, rail_wording.destination) == ("Bergen", "Flåm")
    assert rail_wording.via == ("Myrdal",)
    assert rail_wording.travel_phrase == "Travel from Bergen to Flåm by rail, via Myrdal"
    assert "Bergen Line" not in rail_wording.origin



def test_terminal_destination_is_locality_level_in_day_narrative_for_any_day() -> None:
    coach = {
        "day": "Day 2",
        "type": "Transfer",
        "effective_type": "Transfer",
        "city": "Levi",
        "title": "Coach Transfer to Levi",
        "original_title": "Coach Rovaniemi Bus Station to Levi Bus Station",
        "details": "Coach Rovaniemi Bus Station to Levi Bus Station | Departure 11:40",
    }

    wording = build_client_transport_wording(coach)

    assert wording.arrangement_title == "Coach Transfer from Rovaniemi Bus Station to Levi Bus Station"
    assert wording.day_title == "Coach Transfer to Levi"
    assert wording.travel_phrase == "Travel from Rovaniemi Bus Station towards Levi today by coach"
    assert "Levi Bus Station" not in wording.travel_phrase

def test_local_transfer_supports_arrival_day_without_owning_route_narrative() -> None:
    transfer = _row(
        "Day 1\tTransfer\t01.01.2027\t\tOslo: Private transfer from Oslo Airport to your accommodation"
    )

    assert build_client_transport_wording(transfer).arrangement_title
    assert build_day_client_transport_wording([transfer]) is None


def test_transport_client_copy_ownership_is_explicit() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    transport_domain = root / "itinerary_generation" / "transport_domain"
    direct_consumers = {
        path.name
        for path in transport_domain.glob("*.py")
        if path.name != "client_wording.py" and "build_client_transport_wording(" in path.read_text(encoding="utf-8")
    }

    assert direct_consumers == {"model.py", "render_sequences.py", "titles.py"}
    titles_source = (transport_domain / "titles.py").read_text(encoding="utf-8")
    assert 'return build_client_transport_wording(dict(row)).arrangement_title' in titles_source
    assert 'return build_client_transport_wording(dict(row)).day_title' in titles_source
