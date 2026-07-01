from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editable_draft import normalise_editable_draft
from itinerary_generation.editor_page_contract import build_editor_document_pages
from itinerary_generation.day_render_blocks import build_render_day
from visual_editor_component.editor_payload_builder import build_visual_editor_payload
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_editor_payload_exposes_remaining_static_labels_as_editable_fields():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walking tour"},
    ]

    payload = build_visual_editor_payload(rows, {"Day 1": rows}, {"pictures_added": False})
    pages = build_editor_document_pages(payload=payload, grouped_days={"Day 1": rows})

    assert payload["cover"]["route_label"] == "Route"
    assert payload["summary"]["trip_glance_title"] == "Your Trip at a Glance"
    assert payload["summary"]["journey_arc_title"] == "Your Journey Arc"
    assert payload["summary"]["journey_arc_columns"]["chapter"] == "Chapter"
    assert payload["summary"]["journey_arc_columns"]["days"] == "Days"
    assert payload["summary"]["journey_arc_columns"]["experience"] == "What You’ll Experience"
    assert payload["days"][0]["date"] == ""
    assert next(page for page in pages if page["page_id"] == "cover")["editable_fields"]["route_label"] == "Route"
    assert next(page for page in pages if page["page_id"] == "summary")["editable_fields"]["trip_glance_title"] == "Your Trip at a Glance"
    assert any(page["page_type"] == "final_section" for page in pages)


def test_visual_editor_payload_carries_editable_label_defaults():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walking tour"},
    ]
    payload = build_visual_editor_payload(rows, {"Day 1": rows}, {"pictures_added": False})

    assert payload["cover"]["route_label"] == "Route"
    assert payload["summary"]["trip_glance_title"] == "Your Trip at a Glance"
    assert payload["summary"]["journey_arc_title"] == "Your Journey Arc"
    assert payload["summary"]["journey_arc_columns"]["experience"] == "What You’ll Experience"
    assert payload["final_pages"]["whats_not_included_title"] == "What’s not included"


def test_custom_labels_survive_typed_draft_and_render_contract():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walking tour"},
    ]
    grouped = {"Day 1": rows}
    editor_draft = normalise_editable_draft(
        {
            "cover": {"route_label": "Journey route", "trip_title": "Nordic Escape"},
            "summary": {
                "trip_glance_title": "Trip Snapshot",
                "journey_arc_title": "Trip Flow",
                "journey_arc_columns": {"chapter": "Stage", "days": "When", "experience": "Highlights"},
            },
            "final_pages": {
                "whats_not_included_title": "Excluded services",
                "whats_not_included_html": "<ul><li>Flights</li></ul>",
            },
        }
    )

    context = build_itinerary_render_context(rows, grouped, {"editor_draft": editor_draft})
    html = build_itinerary_html(rows, grouped, {"editor_draft": editor_draft})

    assert context.render_document.cover.route_label == "Journey route"
    assert context.render_document.summary.trip_glance_title == "Trip Snapshot"
    assert context.render_document.summary.journey_arc_title == "Trip Flow"
    assert context.render_document.summary.journey_arc_columns["experience"] == "Highlights"
    assert any(section.title == "Excluded services" for section in context.render_document.final_sections)
    assert "Journey route" in html
    assert "Trip Snapshot" in html
    assert "Trip Flow" in html
    assert "Excluded services" in html


def test_edited_day_date_is_owned_by_typed_draft_for_pdf_contract():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walking tour"},
    ]
    editor_draft = normalise_editable_draft(
        {
            "days": [
                {
                    "day": "Day 1",
                    "date": "12 June 2027",
                    "title": "Edited title",
                    "city": "Oslo",
                    "intro": "Edited intro",
                    "blocks_html": "<div>Edited content</div>",
                }
            ]
        }
    )

    day = build_render_day("Day 1", rows, output_edits={"editor_draft": editor_draft})

    assert day.date == "12 June 2027"
    assert day.title == "Edited title"


def test_page_contract_titles_follow_editable_final_page_titles():
    pages = build_editor_document_pages(
        payload={
            "cover": {},
            "summary": {},
            "days": [],
            "final_pages": {
                "whats_included_title": "Included services",
                "whats_included_pages_html": [{"html": "<div>Hotels</div>"}],
                "important_travel_notes_title": "Before you travel",
                "important_travel_notes_text": "Bring ID.",
            },
        },
        grouped_days={},
    )

    assert next(page for page in pages if page["page_id"] == "final-whats-included")["title"] == "Included services"
    assert next(page for page in pages if page["page_id"] == "final-important-travel-notes")["title"] == "Before you travel"
