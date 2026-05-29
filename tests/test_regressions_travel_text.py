import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from regression_test_helpers import assert_equal, assert_contains, assert_not_contains

from text_polish import (
    expand_time_with_duration,
    polish_client_text,
    polish_hotel_name,
    format_duration_display,
)
from generator import (
    create_whats_included,
    create_journey_arc,
    group_rows_by_day,
    create_day_intro,
    create_trip_glance,
)
from itinerary_generation.titles import create_trip_subtitle
from itinerary_parser import extract_duration_from_description, parse_itinerary
from normalizer import normalize_itinerary_rows
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    DAY_PAGE_LAYOUTS,
    normalize_day_page_layout,
    is_day_packing_enabled,
    is_three_day_packing_enabled,
)

def test_travel_intro_uses_final_transport_destination():
    rows = [
        {"day": "Day 6", "type": "Transfer", "effective_type": "Transfer", "city": "Saariselkä", "title": "Coach Transfer to Rovaniemi Bus Station", "details": "Bus from Saariselkä to Rovaniemi Bus Station"},
        {"day": "Day 6", "type": "Transfer", "effective_type": "Transfer", "city": "Rovaniemi", "title": "Overnight Train to Helsinki", "details": "Overnight Train Transfer with the Santa Claus Express to Helsinki"},
    ]
    intro = create_day_intro(rows, detail_level="Rich descriptive")
    assert_contains(intro, "Saariselkä to Rovaniemi, overnight to Helsinki", "Travel intro should use a natural route label for multi-leg overnight travel.")
    assert_not_contains(intro, "towards Rovaniemi", "Travel intro should not stop at an intermediate station when later transport continues onward.")


def test_departure_block_avoids_duplicate_departure_line():
    from ui.day_blocks import build_departure_block

    block = build_departure_block({"row_id": "departure-1", "title": "Departure"})
    assert_contains(block["html"], "Journey home", "Generic departure rows should get a warmer client-facing line.")
    assert_not_contains(block["html"], '>Departure</div><div class="body-text strong-line">Departure', "Departure block should not repeat the word Departure as both heading and body.")


def test_multiline_supplier_inclusion_commas_are_preserved():
    from parser_modules.details import split_comma_list

    includes = split_comma_list("Access to the Blue Lagoon\nUnlimited use of steam bath, sauna, and cold lagoon\nUse of towel", protect_compound_phrases=True)
    assert_contains("\n".join(includes), "Unlimited use of steam bath, sauna, and cold lagoon", "One supplier inclusion line with natural commas should remain one bullet.")
    assert_not_contains("\n".join(includes), "\nsauna", "Natural comma phrases should not become separate bullets.")

