from __future__ import annotations

from reportlab.platypus import Table
from bs4 import BeautifulSoup

from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.destination_copy import leisure_description
from itinerary_generation.destination_profiles import destination_profile_for, destination_profiles
from itinerary_generation.destination_registry import travel_destination_records
from itinerary_generation.render_model import RenderDay
from pdf_exporter_modules.render_content import render_day_section_pdf
from pdf_exporter_modules.styles import make_styles
from pdf_exporter_modules.typed_exporter import _render_day_story


BAD_KNOWN_DESTINATION_COPY = (
    "the destination",
    "your first impression of the destination",
    "local cafés and neighbourhood life",
    "capital-city streets or local cafés and neighbourhood life",
)


def _arrival_rows(city: str) -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Arrival",
            "effective_type": "Arrival",
            "city": city,
            "title": f"Arrival in {city}",
            "details": "Self-arranged transfer to your accommodation",
        },
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": city,
            "title": "Check in to your accommodation",
            "details": "Two-night stay with breakfast included.",
        },
    ]


def test_destination_profiles_cover_every_registered_travel_destination():
    profiles = destination_profiles()
    records = travel_destination_records()

    assert len(records) >= 600
    assert set(profiles) == {record.name for record in records}

    for record in records:
        profile = profiles[record.name]
        assert profile.identity
        assert profile.arrival_templates
        assert profile.leisure_templates
        assert profile.atmosphere
        assert "the destination" not in profile.identity.casefold()


def test_priority_arrival_intros_use_destination_identity_not_generic_destination():
    expected = {
        "Oslo": "Norwegian capital",
        "Bergen": "historic harbour city and fjord gateway",
        "Stavanger": "fjord gateway",
        "Kristiansand": "Southern Norway’s coastal city",
        "Rovaniemi": "Arctic Circle",
        "Copenhagen": "Danish capital",
        "Reykjavík": "Iceland",
    }

    for city, phrase in expected.items():
        intro = create_day_intro(_arrival_rows(city), detail_level="Rich descriptive")
        assert phrase in intro
        for bad in BAD_KNOWN_DESTINATION_COPY:
            assert bad not in intro


def test_leisure_copy_is_destination_specific_and_varies_by_day_context():
    oslo_day_1 = leisure_description("Oslo", [{"day": "Day 1", "city": "Oslo", "title": "Free time"}])
    oslo_day_2 = leisure_description("Oslo", [{"day": "Day 2", "city": "Oslo", "title": "Free time"}])
    bergen = leisure_description(
        "Bergen",
        [
            {"day": "Day 8", "city": "Bergen", "title": "Guided Walking Tour of Bergen Past & Present"},
            {"day": "Day 8", "city": "Bergen", "title": "Fløibanen Funicular"},
        ],
    )

    assert "Oslo" in oslo_day_1
    assert "Oslo" in oslo_day_2
    assert oslo_day_1 != oslo_day_2
    assert "Bergen" in bergen
    assert "Bryggen" in bergen or "harbourfront" in bergen

    for text in (oslo_day_1, oslo_day_2, bergen):
        for bad in BAD_KNOWN_DESTINATION_COPY:
            assert bad not in text


def test_destination_profile_lookup_has_safe_unknown_fallback_without_destination_wording():
    profile = destination_profile_for("Made Up Nordic Place")
    assert profile.identity == "Made Up Nordic Place and its local setting"
    text = leisure_description("Made Up Nordic Place", [])
    assert "Made Up Nordic Place" in text
    assert "the destination" not in text


def test_pdf_day_intro_no_longer_gets_decorative_divider_line():
    html = """
    <section class="day-section">
      <div class="day-kicker">DAY 1 ✦ OSLO</div>
      <div class="day-title">Welcome to Oslo</div>
      <div class="intro">A destination-aware opening paragraph.</div>
    </section>
    """
    story = []
    render_day_section_pdf(BeautifulSoup(html, "html.parser").select_one(".day-section"), story, make_styles())
    assert not any(isinstance(item, Table) for item in story)

    typed_story = _render_day_story(
        RenderDay(
            day="Day 1",
            number="1",
            city="Oslo",
            title="Welcome to Oslo",
            intro="A destination-aware opening paragraph.",
        ),
        make_styles(),
    )
    assert not any(isinstance(item, Table) for item in typed_story)
