from itinerary_generation.cover_theme import (
    count_rail_travel_rows,
    detect_cover_season,
    get_cover_theme,
    has_northern_lights_activity,
    select_cover_background_key,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_late_november_december_trip_uses_dominant_winter_season():
    rows = _rows("""
    Day 1	Hotel	15	29/11/2026	14/12/2026						Tromso	Hotel, 15xNight, Incl Breakfast
    Day 2	Activity		30/11/2026						Tromso	Northern Lights Chase | 6 PM | 7 Hrs
    """)

    assert detect_cover_season(rows) == "winter"
    assert has_northern_lights_activity(rows)
    assert select_cover_background_key("winter", rows) == "winter_northern_lights"
    assert get_cover_theme(rows)["background_path"].endswith("winter_northern_lights.webp")


def test_autumn_northern_lights_trip_uses_autumn_aurora_cover():
    rows = _rows("""
    Day 1	Hotel	3	10/10/2026	13/10/2026						Rovaniemi	Hotel, 3xNight, Incl Breakfast
    Day 2	Activity		11/10/2026						Rovaniemi	Aurora hunt by minibus | 8 PM | 5 Hrs
    """)

    assert detect_cover_season(rows) == "autumn"
    assert select_cover_background_key("autumn", rows) == "autumn_northern_lights"
    assert get_cover_theme(rows)["background_path"].endswith("autumn_northern_lights.webp")


def test_summer_itinerary_with_two_rail_rows_uses_summer_rail_cover():
    rows = _rows("""
    Day 1	Hotel	1	10/07/2026	11/07/2026						Oslo	Hotel, 1xNight, Incl Breakfast
    Day 2	Transfer		11/07/2026						Flam	Train Oslo to Flåm | 08:00 - 14:00
    Day 3	Activity		12/07/2026						Bergen	Norway in a Nutshell | Flåm to Bergen | 09:00 - 17:00
    """)

    assert detect_cover_season(rows) == "summer"
    assert count_rail_travel_rows(rows) >= 2
    assert select_cover_background_key("summer", rows) == "summer-rail"
    assert get_cover_theme(rows)["background_path"].endswith("summer-rail.webp")


def test_single_summer_rail_row_stays_on_default_summer_cover():
    rows = _rows("""
    Day 1	Hotel	1	10/07/2026	11/07/2026						Oslo	Hotel, 1xNight, Incl Breakfast
    Day 2	Transfer		11/07/2026						Bergen	Train Oslo to Bergen | 08:00 - 14:00
    """)

    assert detect_cover_season(rows) == "summer"
    assert count_rail_travel_rows(rows) == 1
    assert select_cover_background_key("summer", rows) == "summer"
    assert get_cover_theme(rows)["background_path"].endswith("summer.webp")
