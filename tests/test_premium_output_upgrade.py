from __future__ import annotations

from itinerary_generation.transport_domain.render import build_travel_arrangements_render_block
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.custom_final_pages import render_text_paragraph_page
from ui.premium_final_notes import premium_note_cards
from ui.render_blocks import render_block_to_html


def test_important_travel_notes_render_as_premium_guidance_cards():
    cards = premium_note_cards(DEFAULT_IMPORTANT_TRAVEL_NOTES)
    titles = [title for title, _body in cards]

    assert "Transport schedules" in titles
    assert "Hotel timings" in titles
    assert "Optional transfers" in titles
    assert len(cards) == len(DEFAULT_IMPORTANT_TRAVEL_NOTES)

    html = render_text_paragraph_page("Important travel notes", DEFAULT_IMPORTANT_TRAVEL_NOTES)
    assert "premium-notes-page" in html
    assert "premium-notes-grid" in html
    assert html.count("premium-note-card") >= len(DEFAULT_IMPORTANT_TRAVEL_NOTES)


def test_coastal_cruise_transfer_renders_as_premium_arrangement_card():
    rows = [
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Stavanger",
            "title": "Private transfer to Stavanger Cruise Port",
            "details": "Stavanger: Private transfer to Stavanger Cruise Port",
        },
        {
            "type": "Cruise",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Atlantic Coastal Cruise Transfer to Bergen",
            "details": "Stavanger: Atlantic Coastal Cruise Transfer to Bergen - Time: 07:30 am - 1:00 pm - Meeting point: Stavanger Cruise Port - Includes: Tickets, Fjord Lounge",
            "time": "07:30 am - 1:00 pm",
            "includes": ["Tickets", "Fjord Lounge"],
        },
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Bergen",
            "title": "Private transfer to your accommodation",
            "details": "Bergen: Private transfer to your accommodation",
        },
    ]

    block = build_travel_arrangements_render_block(rows)

    assert block is not None
    assert "coastal-cruise-card" in block.css_class
    assert block.title == "Stavanger → Bergen"
    assert any(meta.label == "Time" and "7:30 AM - 1:00 PM" in meta.value for meta in block.meta)

    html = render_block_to_html(block)["html"]
    assert "Atlantic Coastal Cruise Transfer to Bergen" in html
    assert "premium-travel-timeline" in html
    assert "Coordinated day flow" not in html  # timeline replaces debug-style section labels
    assert "Fjord Lounge" in html
    assert "Stavanger → Bergen" in html


def test_norway_in_a_nutshell_renders_as_featured_scenic_journey():
    rows = [
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Bergen",
            "title": "Self transfer to Bergen Train Station",
            "details": "Bergen: Self transfer to Bergen Train Station",
        },
        {
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Bergen",
            "title": "Norway in a Nutshell to Oslo",
            "details": "Bergen: Norway in a Nutshell to Oslo - Time: 08:29 am - 10:27 pm - Meeting point: Bergen Train Station - Includes: Train transfer Bergen to Voss (08:29 am - 09:41 am), Coach transfer Voss to Gudvangen (10:10 am - 11:10 am), Fjord Cruise Gudvangen to Flåm (12:10 pm - 2:10 pm), Train transfer Flåm to Myrdal (4:00 pm - 4:57 pm), Train Transfer Myrdal to Oslo (5:40 pm - 10:27 pm)",
            "time": "08:29 am - 10:27 pm",
            "includes": [
                "Train transfer Bergen to Voss (08:29 am - 09:41 am)",
                "Coach transfer Voss to Gudvangen (10:10 am - 11:10 am)",
                "Fjord Cruise Gudvangen to Flåm (12:10 pm - 2:10 pm)",
                "Train transfer Flåm to Myrdal (4:00 pm - 4:57 pm)",
                "Train Transfer Myrdal to Oslo (5:40 pm - 10:27 pm)",
            ],
        },
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "title": "Self transfer to your accommodation",
            "details": "Oslo: Self transfer to your accommodation",
        },
    ]

    block = build_travel_arrangements_render_block(rows)

    assert block is not None
    assert block.section_title == "Featured Scenic Journey"
    assert "featured-journey-block" in block.css_class
    assert block.title == "Norway in a Nutshell to Oslo"
    assert any("Norway in a Nutshell to Oslo" in line and "8:29 AM - 10:27 PM" in line for line in block.lines)

    html = render_block_to_html(block)["html"]
    assert "premium-route-ribbon" in html
    assert "Bergen → Voss → Gudvangen → Flåm → Myrdal → Oslo" in html
    assert "Self-guided scenic journey" in html
    assert "Bergen Railway" in html
    assert "Flåm Railway" in html
    assert "Nærøyfjord cruise" in html
