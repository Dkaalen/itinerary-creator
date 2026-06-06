import json
from pathlib import Path
import sys
import types

streamlit_stub = types.SimpleNamespace(
    warning=lambda *args, **kwargs: None,
    success=lambda *args, **kwargs: None,
    session_state={},
    components=types.SimpleNamespace(
        v1=types.SimpleNamespace(declare_component=lambda *args, **kwargs: (lambda **component_kwargs: None))
    ),
)
sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", streamlit_stub.components)
sys.modules.setdefault("streamlit.components.v1", streamlit_stub.components.v1)

from images.matcher_context import build_day_context
from images.matcher_scoring import score_image_for_day
from images.metadata import ImageCandidate
from parser_modules.extractors import extract_meeting_point_from_description
from parser_modules.transport_titles import standardize_private_transfer_title
from ui.travel_sequence_blocks import build_travel_arrangements_block
from visual_editor_component.editor_workflow import apply_visual_editor_result
from ui.day_page_sections import render_day_section


def _visual_editor_frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    parts = [(frontend / "index.html").read_text(encoding="utf-8")]
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/images.js",
        "js/render.js",
        "js/serialization.js",
        "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_pdf_export_commit_persists_full_visible_editor_model():
    output_edits = {"days": {}}
    result = json.dumps({
        "commit_nonce": "44",
        "payload": {
            "cover": {"trip_title": "Edited title"},
            "summary": {},
            "days": [
                {"day": "Day 2", "title": "Edited Day Title", "blocks_html": "<div>Edited day block</div>"}
            ],
            "final_pages": {
                "whats_included_pages_html": [
                    {"html": "<div>Private transfers</div>"},
                    {"html": "<div>Rail journeys moved by editor</div>"},
                ]
            },
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["trip_title"] == "Edited title"
    assert output_edits["days"]["Day 2"]["title"] == "Edited Day Title"
    assert output_edits["days"]["Day 2"]["blocks_html"] == "<div>Edited day block</div>"
    assert output_edits["whats_included_pages_html"] == [
        "<div>Private transfers</div>",
        "<div>Rail journeys moved by editor</div>",
    ]


def test_visual_editor_frontend_has_page_controls_and_full_commit_contract():
    editor_html = _visual_editor_frontend_source()

    assert "Remove empty page" in editor_html
    assert "Move content up" in editor_html
    assert "deleteInclusionPage" in editor_html
    assert "mergeInclusionPageUp" in editor_html
    assert "compactFullPayloadForCommit" in editor_html
    assert "PDF export is the hard commit point" in editor_html
    assert "insertCleanClipboardHtml" in editor_html


def test_polar_icebreaker_default_image_requires_icebreaker_activity():
    candidate = ImageCandidate(
        path="/fake/Default_Winter_Polar_Icebreaker_01.webp",
        country="",
        city="Default",
        filename="Default_Winter_Polar_Icebreaker_01",
        tokens=("default", "icebreaker", "polar", "polaricebreaker", "winter"),
        themes=("winter",),
        seasons=("winter",),
    )
    hotel_context = build_day_context("Day 3", [
        {"type": "Hotel", "effective_type": "Hotel", "city": "Rovaniemi", "title": "Original Sokos Hotel Vaakuna Rovaniemi", "date": "16/11/2026"}
    ])
    score, reasons = score_image_for_day(candidate, hotel_context)
    assert score == 0
    assert "protected specialty" in reasons[0]

    activity_context = build_day_context("Day 5", [
        {"type": "Activity", "effective_type": "Activity", "city": "Rovaniemi", "title": "Polar Icebreaker Cruise", "date": "18/11/2026"}
    ])
    activity_score, _ = score_image_for_day(candidate, activity_context)
    assert activity_score > 0


def test_meeting_point_extraction_stops_before_supplier_metadata():
    text = (
        "Rovaniemi: Meet Santa Claus |08:30 AM | 5 hrs Pick up / meeting point : "
        "Santa's Hotel Santa Claus, Korkalonkatu 29, Rovaniemi What's included? "
        "Hotel or accommodation transfer Max 8 participants What to expect? Supplier prose"
    )

    assert extract_meeting_point_from_description(text) == "Santa's Hotel Santa Claus, Korkalonkatu 29, Rovaniemi"


def test_generic_private_airport_uses_city_airport_not_private_airport():
    assert standardize_private_transfer_title("Private Airport to Hotel", "Private Airport to Hotel", "Helsinki") == (
        "Private transfer from Helsinki Airport to your accommodation"
    )


def test_santa_claus_express_day_block_keeps_schedule_and_cabin():
    block = build_travel_arrangements_block([
        {
            "type": "Transfer",
            "effective_type": "Train",
            "title": "Santa Claus Express to Rovaniemi",
            "original_title": "Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 4 x downstairs cabin for two people",
            "details": "Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 4 x downstairs cabin for two people",
            "time": "11:13 PM - 10:59 AM",
            "duration": "",
            "includes": [],
            "city": "Helsinki",
        }
    ])

    html = block["html"]
    assert "Santa Claus Express to Rovaniemi" in html
    assert "11:13 PM - 10:59 AM" in html
    assert "Cabin: 4 x downstairs cabin for two people" in html


def test_pdf_bound_day_rendering_respects_intentionally_empty_editor_block():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Rovaniemi",
            "title": "Generated Snowmobile Safari",
            "client_description": "Generated activity details",
            "time": "10:00 AM",
        }
    ]
    output_edits = {"days": {"Day 1": {"blocks_html": ""}}}

    html = render_day_section("Day 1", rows, output_edits)

    assert "activity-block" not in html
    assert "Generated activity details" not in html
