from __future__ import annotations

from pathlib import Path

from parser_modules.extractors import (
    extract_duration_from_description,
    extract_includes_from_description,
    extract_meeting_point_from_description,
    extract_time_from_description,
)

ROOT = Path(__file__).resolve().parents[1]


def test_parser_extractors_facade_delegates_to_focused_modules() -> None:
    facade = ROOT / "parser_modules" / "extractors.py"
    assert len(facade.read_text(encoding="utf-8").splitlines()) < 40

    assert (ROOT / "parser_modules" / "extract_time.py").exists()
    assert (ROOT / "parser_modules" / "extract_meeting_point.py").exists()
    assert (ROOT / "parser_modules" / "extract_inclusions.py").exists()


def test_messy_pipe_activity_extracts_time_duration_meeting_point_and_inclusions() -> None:
    source = (
        "Rovaniemi: Northern Lights Hunt by Minibus at the Arctic Circle | 8 PM | 3 Hrs | "
        "Pick up / meeting point ,Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi | "
        "Pick-up/drop off in central Rovaniemi ,Professional, English-speaking guide ,"
        "Winter overalls, boots and gloves ,Warm juice and cookies"
    )

    assert extract_time_from_description(source) == "8:00 PM"
    assert extract_duration_from_description(source) == "3 hours"
    assert extract_meeting_point_from_description(source) == "Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi"
    assert extract_includes_from_description(source) == [
        "Pick-up/drop-off in central Rovaniemi",
        "Professional, English-speaking guide",
        "Winter overalls, boots and gloves",
        "Warm juice and cookies",
    ]


def test_run_on_supplier_sections_still_extract_clean_inclusions() -> None:
    source = (
        "Copenhagen: City Walking & Canal Tour incl. Change of Guards | 09:00 | 3 Hrs "
        "Pick up / meeting point : Copenhagen Central Station, København\nOverview\nSee Copenhagen’s top sights."
        "\nWhat's included?\nWalking tour by born-and-raised host\nPersonalized, small-group experience\n"
        "Harbor ferry ride through the canals\nChange of guards at the royal palace\nWhat to expect?\nSee Copenhagen."
    )

    assert extract_meeting_point_from_description(source) == "Copenhagen Central Station, København"
    assert extract_includes_from_description(source) == [
        "Walking tour by born-and-raised host",
        "Personalized, small-group experience",
        "Harbor ferry ride through the canals",
        "Change of guards at the royal palace",
    ]


def test_parallel_supplier_time_options_are_paired_by_position():
    source = (
        "Helsinki: A Finntastic Walking Tour - Time: "
        "10:30 am / 1:30 pm - 12:45 pm / 3:45 pm - Meeting point: Senate Square"
    )

    assert extract_time_from_description(source) == "10:30 AM - 12:45 PM / 1:30 PM - 3:45 PM"
