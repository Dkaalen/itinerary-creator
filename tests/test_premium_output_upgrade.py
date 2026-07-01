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
    assert "Northern Lights" in titles
    assert "Winter travel conditions" in titles
    assert "Extra nights" not in titles
    assert "Optional transfers" not in titles
    assert "Tailor-made additions" not in titles
    assert len(cards) == len(DEFAULT_IMPORTANT_TRAVEL_NOTES)

    html = render_text_paragraph_page("Important travel notes", DEFAULT_IMPORTANT_TRAVEL_NOTES)
    assert "premium-notes-page" in html
    assert "premium-notes-grid" in html
    assert html.count("premium-note-card") >= len(DEFAULT_IMPORTANT_TRAVEL_NOTES)


def test_coastal_cruise_transfer_renders_as_native_travel_arrangement():
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
    assert block.css_class == "travel-sequence-block"
    assert "premium-travel-card" not in block.css_class
    assert block.title == "Stavanger → Bergen"
    assert any(meta.label == "Time" and "7:30 AM - 1:00 PM" in meta.value for meta in block.meta)

    html = render_block_to_html(block)["html"]
    assert "Coastal cruise" in html
    assert "Stavanger → Bergen · 7:30 AM - 1:00 PM" in html
    assert "premium-travel-timeline" not in html
    assert "premium-travel-card" not in html
    assert "Journey sequence" in html
    assert "Style:" not in html
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
    assert block.css_class == "travel-sequence-block"
    assert "premium-travel-card" not in block.css_class
    assert block.title == "Norway in a Nutshell to Oslo"
    assert block.lines == []

    html = render_block_to_html(block)["html"]
    assert "premium-route-ribbon" not in html
    assert "premium-travel-card" not in html
    assert "Bergen → Voss → Gudvangen → Flåm → Myrdal → Oslo" in html
    assert "Style:" not in html
    assert "Bergen Railway" in html
    assert "Flåm Railway" in html
    assert "Nærøyfjord cruise" in html
    assert "premium-travel-timeline-label" not in html
    assert "Rail segment" in html
    assert "Scheduled rail, coach and fjord-cruise tickets as listed" in html

    linked = next(section for section in block.extra_sections if section.title == "Linked transfers")
    linked_text = "\n".join(linked.items)
    assert "Bergen: Self-arranged" not in linked_text
    assert "Oslo: Self-arranged" not in linked_text
    assert linked.items == [
        "Self-arranged transfer to Bergen Railway Station",
        "Self-arranged transfer to your accommodation",
    ]


def test_self_transfer_rows_do_not_duplicate_title_and_details_in_native_travel_blocks():
    rows = [
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "title": "Self transfer to Oslo Central Station",
            "details": "Oslo: Self transfer to Oslo Central Station",
        }
    ]

    block = build_travel_arrangements_render_block(rows)
    html = render_block_to_html(block)["html"]

    assert "Self-arranged transfer to Oslo Central Station" in html
    assert "Oslo: Self-arranged transfer" not in html
    assert html.count("Self-arranged transfer") == 1


def test_retired_special_travel_widget_classes_are_not_in_runtime_contracts():
    from pathlib import Path
    from visual_editor_component.style_presets import extra_allowed_classes

    retired = {
        "premium-travel-card",
        "premium-travel-timeline",
        "premium-travel-title",
        "premium-route-ribbon",
        "premium-linked-transfers",
        "featured-journey-block",
        "coastal-cruise-card",
    }

    assert retired.isdisjoint(set(extra_allowed_classes()))
    runtime_files = [
        Path("app_modules/itinerary_html_styles.py"),
        Path("visual_editor_component/frontend/styles/editor.css"),
        Path("visual_editor_component/frontend/js/style_preset_data.js"),
        Path("pdf_exporter_modules/render_content.py"),
        Path("pdf_exporter_modules/typed_exporter.py"),
        Path("ui/render_blocks.py"),
    ]
    runtime_text = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
    for class_name in retired:
        assert class_name not in runtime_text
