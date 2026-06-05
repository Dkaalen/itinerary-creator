from generator import create_day_title, group_rows_by_day
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.transport import get_transfer_travel_title
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.travel_sequence_blocks import get_travel_arrangement_line, _norway_nutshell_lines


FIXTURE_TEXT = """
	Day 4	Activity		27/10/2026								Rovaniemi	Rovaniemi: Small-Group Aurora Hunt by Minibus - Time: 7:00 pm - 10:00 pm
	Day 4	Activity		27/10/2026								Rovaniemi	Rovaniemi: Northern Lights Ice Floating - Time: 8:00 pm - 11:00 pm - Includes: Thermal survival suit, Floating in a frozen lake, Warm drinks and cookies
	Day 5	Transfer 		28/10/2026								Kakslauttenen	Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Kakslauttenen Arctic Resort - 11:45 am - 3:02 pm - Tickets Included
	Day 7	Activity		30/10/2026								Tromso	Tromsø: Photo Tour to Arctic Landscapes and Fjords - Time: 10:00 am - 3:00 pm - Includes: Professional photo guides, Scenic fjord safari by comfortable minivan vehicle, Help with camera settings and nature photography, Reindeer sometimes wander through this landscape, Soup and coffee
	Day 9	Transfer		01/11/2026								Oslo	Norway in a Nutshell | Bergen to Oslo | 8:30 am - 10:30 pm | Includes: Train Bergen to Voss, Bus to Gudvangen, Fjord cruise, Flåm Railway, Bergen Railway to Oslo
"""


def _rows_by_day():
    return group_rows_by_day(normalize_itinerary_rows(parse_itinerary(FIXTURE_TEXT)))


def test_photo_fjord_tour_description_beats_incidental_reindeer_keyword():
    row = _rows_by_day()['Day 7'][0]

    block = canonical_activity_block(row)

    assert 'photo-focused excursion' in block.description
    assert 'fjords and coastal scenery' in block.description
    assert 'Meet and feed reindeer' not in block.description


def test_ice_floating_description_beats_generic_northern_lights_template():
    row = _rows_by_day()['Day 4'][1]

    block = canonical_activity_block(row)

    assert 'Float in a frozen lake' in block.description
    assert 'thermal survival suit' in block.description
    assert 'Head out in search of the Northern Lights' not in block.description


def test_coach_transfer_day_title_and_line_strip_time_and_ticket_noise():
    row = _rows_by_day()['Day 5'][0]

    assert create_day_title(_rows_by_day()['Day 5']) == 'Coach Transfer to Kakslauttanen'
    assert get_transfer_travel_title(row) == 'Coach Transfer to Kakslauttanen'
    line = get_travel_arrangement_line(row)
    assert line == 'Coach Transfer to Kakslauttanen — 11:45 AM - 3:02 PM'
    assert 'Tickets Included' not in line


def test_norway_in_a_nutshell_travel_line_preserves_timing():
    row = _rows_by_day()['Day 9'][0]

    lines = _norway_nutshell_lines(row)

    assert lines[0] == 'Norway in a Nutshell from Bergen to Oslo — 8:30 AM - 10:30 PM'


def test_generic_cable_car_viewpoint_ticket_gets_flexible_ticket_wording():
    row = {
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Tromsø",
        "title": "Round trip cable car ticket to the mountain viewpoint",
        "details": "Tickets only. Valid for a flexible visit during opening hours.",
        "includes": ["Round-trip cable car ticket"],
    }

    block = canonical_activity_block(row)

    assert "flexible visit" in block.description
    assert "view" in block.description.lower()
    assert "Tickets only" not in block.description


def test_anytime_activity_range_is_labelled_as_start_window():
    row = {
        "row_id": "santa-anytime",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Rovaniemi",
        "title": "City Highlights, Santa Village & Husky-Reindeer Safari",
        "original_title": "City Highlights, Santa Village & Husky-Reindeer Safari | 8-10 AM (Anytime )| 7 Hrs",
        "details": "City Highlights, Santa Village & Husky-Reindeer Safari | 8-10 AM (Anytime )| 7 Hrs",
        "time": "8:00 AM - 10:00 AM",
        "duration": "7 hours",
        "display_time": "8:00 AM - 10:00 AM",
        "display_duration": "7 hours",
        "includes": ["Sightseeing at Santa Claus Village"],
    }

    block = canonical_activity_block(row)

    assert any(line.label == "Start window" and line.value == "8:00 AM - 10:00 AM" for line in block.meta)
    assert any(line.label == "Duration" and line.value == "7 hours" for line in block.meta)


def test_ambiguous_tromso_round_trip_ticket_stays_generic_and_warns():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows
    from itinerary_generation.canonical_activity import canonical_activity_block

    raw = """
    Day 1	Activity	02/11/2026		Tromso	Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.
    """
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    block = canonical_activity_block(rows[0])

    assert block.title == "Round-trip viewpoint ticket in Tromsø"
    assert "Fjellheisen" not in block.title
    assert "Fjellheisen" not in block.description
    assert "ambiguous_activity_title" in block.warnings
