from pathlib import Path

from generator import create_day_title, group_rows_by_day
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.transport import get_transfer_travel_title
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.travel_sequence_blocks import get_travel_arrangement_line, _norway_nutshell_lines


FIXTURE_TEXT = Path('/mnt/data/Pasted text.txt').read_text(encoding='utf-8')


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

    assert lines[0] == 'Norway in a Nutshell to Oslo — 8:30 AM - 10:30 PM'
