import json
from pathlib import Path

from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.canonical_builder import canonical_accommodation_block
from itinerary_generation.inclusion_hotels import hotel_line


FIXTURE_PATH = Path("tests/fixtures/quality_stress_inputs/accommodation/accommodation_inputs.json")


def _hotel_row(raw_details: str):
    raw = f"Day 1\tHotel\t01.01.2027\t02.01.2027\t{raw_details}"
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    assert len(rows) == 1
    return rows[0]


def test_accommodation_stress_fixture_bank_is_available_for_future_patches():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(records) == 50
    assert {record["bank"] for record in records} == {"accommodation"}
    assert {"multi_room", "glass_igloo", "apartment", "villa", "messy_room"}.issubset(
        {record["category"] for record in records}
    )


def test_accommodation_preserves_multi_room_quantities_and_bed_type():
    row = _hotel_row(
        "Bergen: Check in for 2 nights - Hotel Norge - 2x Family rooms, 4x std. double rooms - King bed - breakfast included"
    )

    assert row["hotel_name"] == "Hotel Norge"
    assert row["hotel_nights"] == "2"
    assert row["room_category"] == "2 x Family Room, 4 x Standard Double Room - king bed"
    assert row["meal_plan"] == "breakfast"

    block = canonical_accommodation_block(row)
    assert block.title == "Hotel Norge in Bergen for 2 nights"
    assert block.lines == ["Room category: 2 x Family Room, 4 x Standard Double Room - king bed, breakfast included"]

    summary = hotel_line(row)
    assert "Hotel Norge, Bergen" in summary
    assert "2 nights. 2 x Family Room, 4 x Standard Double Room - king bed. Breakfast included." in summary


def test_accommodation_keeps_apartment_quantity_and_without_breakfast_status():
    row = _hotel_row(
        "Copenhagen: 3 night stay - Adina Apartment Hotel - 1 x One Bedroom Apartment - breakfast not included"
    )

    assert row["hotel_name"] == "Adina Apartment Hotel"
    assert row["hotel_nights"] == "3"
    assert row["room_category"] == "1 x One Bedroom Apartment"
    assert row["meal_plan"] == "without breakfast"

    block = canonical_accommodation_block(row)
    assert block.title == "Adina Apartment Hotel in Copenhagen for 3 nights"
    assert block.lines == ["Room category: 1 x One Bedroom Apartment, without breakfast"]


def test_accommodation_does_not_use_meal_or_room_fragment_as_hotel_name():
    igloo = _hotel_row("Kakslauttanen: Check-in for 1 night - 1 x Small Glass Igloo - half board included")
    villa = _hotel_row("Lofoten: Check into seaside villa for 4 nights - 1 x Three Bedroom Villa - self catering")

    assert igloo["hotel_name"] == "Accommodation"
    assert igloo["room_category"] == "1 x Small Glass Igloo"
    assert igloo["meal_plan"] == "half board"
    assert canonical_accommodation_block(igloo).title == "Accommodation in Kakslauttanen for 1 night"
    assert canonical_accommodation_block(igloo).lines == ["Room category: 1 x Small Glass Igloo, half board included"]

    assert villa["hotel_name"] == "Accommodation"
    assert villa["room_category"] == "1 x Three Bedroom Villa"
    assert villa["meal_plan"] == "self catering"
    assert canonical_accommodation_block(villa).title == "Accommodation in Lofoten for 4 nights"
    assert canonical_accommodation_block(villa).lines == ["Room category: 1 x Three Bedroom Villa, self-catering"]


def test_accommodation_normalizes_messy_nites_and_breakfast_typo():
    row = _hotel_row(
        "Stockholm: Hotel Sign - 2 nites - 8 x Superior doubel room - King bed - brekafast inclueded"
    )

    assert row["hotel_name"] == "Hotel Sign"
    assert row["hotel_nights"] == "2"
    assert row["room_category"] == "8 x Superior Double Room - king bed"
    assert row["meal_plan"] == "breakfast"
    assert canonical_accommodation_block(row).title == "Hotel Sign in Stockholm for 2 nights"
