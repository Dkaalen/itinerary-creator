from pathlib import Path

from itinerary_generation.activity_training_catalogue import (
    activity_training_entries,
    catalogue_description_for_row,
    match_activity_training_entry,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.render_helpers import get_activity_description


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_activity_training_catalogue_is_bundled_for_future_fixtures():
    entries = activity_training_entries()

    assert len(entries) >= 100
    assert any(entry.title == "Helsinki City Highlights & Suomenlinna Day Tour" for entry in entries)
    assert any(entry.title == "Northern Lights Hunt by Minibus at the Arctic Circle" for entry in entries)
    assert Path("itinerary_generation/data/activity_training_master_3col.tsv").exists()
    assert Path("tests/fixtures/activity_training/raw_messy_activity_source.txt").exists()
    assert Path("tests/fixtures/activity_training/structured_activity_master_3col.tsv").exists()


def test_messy_pipe_activity_keeps_meeting_point_and_inclusions_separate():
    raw = """
Day 1	Activity	01/06/2026									Rovaniemi	Rovaniemi: Northern Lights Hunt by Minibus at the Arctic Circle | 8 PM | 3 Hrs | Pick up / meeting point ,Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi | Pick-up/drop off in central Rovaniemi ,Professional, English-speaking guide ,Winter overalls, boots and gloves ,Warm juice and cookies
"""
    row = _rows(raw)[0]

    assert row["title"] == "Northern Lights Hunt by Minibus at the Arctic Circle"
    assert row["display_time"] == "8:00 PM - 11:00 PM"
    assert row["meeting_point"] == "Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi"
    assert "Pick-up/drop-off in central Rovaniemi" in row["includes"]
    assert "Professional, English-speaking guide" in row["includes"]
    assert "Pick-up/drop-off" not in row["meeting_point"]


def test_training_catalogue_can_supply_clean_descriptions_without_echoing_pipe_metadata():
    raw = """
Day 1	Activity	01/06/2026									Helsinki	Helsinki: City Highlights & Suomenlinna Day Tour | 10 AM | 5 Hrs | Hotel pick-up (selected hotels), Transport by A/C coach or minivan, Professional, English-speaking guide, Round-trip ferry is included
"""
    row = _rows(raw)[0]
    description = get_activity_description(row)

    assert row["title"] == "Helsinki City Highlights & Suomenlinna Day Tour"
    assert "coach/minivan" in description
    assert "Suomenlinna" in description
    assert "Time:" not in description
    assert "Meeting point:" not in description


def test_catalogue_match_is_conservative_but_usable_for_known_variants():
    entry = match_activity_training_entry(
        "Tromsø: Northern Lights Safari to Aurora Basecamp | 18:15 | 7 Hrs | Pick-up/drop-off in central Tromsø",
        city="Tromso",
        source_title="Northern Lights Safari to Aurora Basecamp",
    )

    assert entry is not None
    assert entry.city == "Tromsø"
    assert entry.title == "Northern Lights Safari to Aurora Basecamp"
    assert catalogue_description_for_row({
        "city": "Tromso",
        "title": "Northern Lights Safari to Aurora Basecamp",
        "details": "Tromsø: Northern Lights Safari to Aurora Basecamp | 18:15 | 7 Hrs",
    })
