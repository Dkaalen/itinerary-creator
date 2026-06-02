from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from generator import group_rows_by_day
from itinerary_generation.inclusions import create_whats_not_included
from itinerary_generation.validation import validate_itinerary_integrity


def _rows(raw):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_supplier_on_request_text_does_not_turn_later_rows_optional():
    raw = '''
Day 1	Hotel	23/12/2026	25/12/2026					Helsinki	4 Star, Scandic Grand Marina, 1xNight, 1xStandard Double Room, Incl Brekafast
Day 2	Activity	24/12/2026						Helsinki	Helsinki: City Highlights & Suomenlinna Day Tour | 10 AM | 5 Hrs | What's included? Professional guide, Round-trip ferry | What to expect? Other languages available on request (Dutch, German, French, Italian, Spanish, Chinese)
Day 3	Transfer	25/12/2026						Helsinki	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 07:30 pm - 07:20 AM next day - 1 x downstairs cabin for two people
Day 4	Hotel	26/12/2026	28/12/2026					Rovaniemi	3 Star, Hotel Aakenus, 2xNight, 1xStandard Twin Room, Incl Brekafast
Day 6	Transfer	28/12/2026						Rovaniemi	Private Transfer to Glass Igloo Stay
Day 7	Transfer	29/12/2026						Tromso	Arctic Coach Rovaniemi to Tromso | 11:00 (Arrives 19:30)
Day 9	Transfer	31/12/2026						Bergen	Flight tromso to Bergen self arrange cost not included
Day 11	Transfer	02/01/2027						Oslo	Norway in a NUtshell | Bergen to Oslo |08:30 - 22:30 | Including luggage porter service
Day 13	Transfer	04/01/2027						Oslo	Self Transfer Hotel to Airport
'''
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    assert "Day 13" in grouped
    assert any(row.get("city") == "Bergen" for row in grouped["Day 9"])
    assert not any(row.get("is_optional") for row in rows if row.get("day") in {"Day 6", "Day 7", "Day 9", "Day 11", "Day 13"})
    assert not [issue for issue in validate_itinerary_integrity(rows) if issue.severity == "error"]


def test_explicit_optional_row_stays_out_of_main_itinerary_and_exclusions_name_it():
    raw = '''
Day 1	Hotel	05.08.2026	07.08.2026					Oslo	Oslo: Clarion Hotel The Hub - Standard Double Room - Breakfast included
Day 2	Activity	06.08.2026						Oslo	Oslo: Fjord Sightseeing Cruise - Time: 11:00 am - 1:00 pm - Includes: Oslofjord archipelago cruise by electric boat
Day 3	Optional	07.08.2026						Oslo	Oslo: Second Walrus Safari Boat Tour - Time: 09:00 am - 1:00 pm - Meeting point: Hotel pick up - Includes: Transfer to/from the harbour, Boat tour onboard Kvitbjørn
Day 4	Transfer	08.08.2026						Oslo	Self Transfer Hotel to Airport
'''
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    optional_rows = [row for row in rows if row.get("is_optional")]
    assert len(optional_rows) == 1
    assert optional_rows[0].get("effective_type") == "Activity"
    main_text = "\n".join(row.get("title", "") for day_rows in grouped.values() for row in day_rows)
    assert "Second Walrus" not in main_text
    not_included = "\n".join(create_whats_not_included(rows))
    assert "Optional experiences unless specifically confirmed" in not_included
    assert "Second Walrus Safari Boat Tour" in not_included
    assert "Self-arranged flights or transport" in not_included
    assert "Self Transfer" in not_included or "Self transfer" in not_included


def test_validation_blocks_truncated_main_itinerary_when_late_rows_are_optional():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Helsinki", "is_optional": False},
        {"day": "Day 5", "type": "Activity", "effective_type": "Activity", "city": "Rovaniemi", "is_optional": False},
        {"day": "Day 6", "type": "Hotel", "effective_type": "Hotel", "city": "Rovaniemi", "is_optional": True, "commercial_status": "optional"},
        {"day": "Day 13", "type": "Transfer", "effective_type": "Transfer", "city": "Oslo", "is_optional": True, "commercial_status": "optional"},
    ]
    issues = validate_itinerary_integrity(rows)
    assert any(issue.code == "main_itinerary_truncated_by_optional_rows" for issue in issues)
