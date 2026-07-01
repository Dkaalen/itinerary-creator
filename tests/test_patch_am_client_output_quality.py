from __future__ import annotations

import sys
import types
from pathlib import Path

st_module = types.ModuleType("streamlit")
st_module.session_state = {}
st_module.warning = lambda *a, **k: None
st_module.success = lambda *a, **k: None
components_module = types.ModuleType("streamlit.components")
v1_module = types.ModuleType("streamlit.components.v1")
v1_module.declare_component = lambda *a, **k: (lambda **kwargs: None)
components_module.v1 = v1_module
st_module.components = components_module
sys.modules.setdefault("streamlit", st_module)
sys.modules.setdefault("streamlit.components", components_module)
sys.modules.setdefault("streamlit.components.v1", v1_module)

from app_modules.itinerary_html import build_itinerary_html
from generator import create_destinations_line, create_journey_arc, create_trip_glance, group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.inclusion_pages import paginate_categorized_inclusions, render_categorized_inclusions_pages, render_inclusion_sections_inner_html
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
from visual_editor_component.editor_workflow import build_visual_editor_payload

ROOT = Path(__file__).resolve().parents[1]

from tests.frontend_asset_helpers import read_resolved_frontend_css


def _visual_editor_frontend_source() -> str:
    frontend = ROOT / "visual_editor_component" / "frontend"
    parts = [
        (frontend / "index.html").read_text(encoding="utf-8"),
        read_resolved_frontend_css(),
    ]
    for relative in (
        "js/state.js",
        "js/images.js",
        "js/render.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
        "js/editor_text_tools.js",
        "js/editor_document_model.js",
        "js/editor_inspector.js",
        "js/editor_page_actions.js",
        "js/editor_warnings.js",
        "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)


def _rows(raw: str) -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(raw))


def _polluted_winter_rows() -> list[dict]:
    return _rows(
        """
Day 1	Transfer 		28/10/2026					Helsinki	Private Airport to your hotel
Day 1	Hotel	1	28/10/2026	29/10/2026				Helsinki	Hotel Haven, 1xNight, Incl Breakfast
Day 2	Activity		29/10/2026					Helsinki	Day Excursion to Tallinn
Day 2	Transfer		29/10/2026					Rovaniemi Railway	Santa Claus Express from Helsinki to Rovaniemi Railway
Day 2	Hotel	2	29/10/2026	31/10/2026				Rovaniemi	Arctic City Hotel, 2xNight, Incl Breakfast
Day 4	Transfer		31/10/2026					Rovaniemi	Private transfer from Rovaniemi Railway to your accommodation Private
Day 4	Hotel	1	31/10/2026	01/11/2026				Kakslauttanen	Kakslauttanen Arctic Resort, 1xNight, Incl Breakfast
Day 5	Transfer		01/11/2026					Kakslauttanen	Shuttle transfer from Kakslauttanen to Ivalo Airport
Day 5	Flight		01/11/2026					Ivalo	Flight from Ivalo to Tromsø
Day 5	Hotel	2	01/11/2026	03/11/2026				Tromso	Clarion Hotel The Edge, 2xNight, Incl Breakfast
"""
    )


def test_route_and_trip_glance_are_owned_by_overnight_destinations_only():
    rows = _polluted_winter_rows()
    grouped = group_rows_by_day(rows)

    assert create_destinations_line(rows) == "Helsinki · Rovaniemi · Kakslauttanen · Tromsø"
    glance = create_trip_glance(rows, grouped)
    assert glance["Start"] == "Helsinki"
    assert glance["End"] == "Tromsø"
    assert glance["Destinations"] == "Helsinki · Rovaniemi · Kakslauttanen · Tromsø"

    polluted_terms = ["your hotel", "your accommodation", "Rovaniemi Railway", "Ivalo", "Tallinn", "Private"]
    route_text = "\n".join([create_destinations_line(rows), str(glance)])
    for term in polluted_terms:
        assert term not in route_text


def test_saved_polluted_route_and_glance_are_sanitized_before_rendering_or_editor_payload():
    rows = _polluted_winter_rows()
    grouped = group_rows_by_day(rows)
    output_edits = {
        "destinations_line": "Helsinki · your hotel · Rovaniemi Railway · your accommodation Private · Kakslauttanen · Ivalo · Tromsø",
        "trip_glance": {
            "Start": "your hotel",
            "End": "your accommodation Private",
            "Destinations": "Helsinki · your hotel · Rovaniemi Railway · Ivalo · Tromsø",
        },
        "journey_arc": [
            {"chapter": "Bergen", "days": "8", "experience": "Onward flight and accommodation"},
        ],
        "pictures_added": False,
    }

    html = build_itinerary_html(rows, grouped, output_edits)
    payload = build_visual_editor_payload(rows, grouped, output_edits)

    assert "Helsinki · Rovaniemi · Kakslauttanen · Tromsø" in html
    assert payload["cover"]["destinations_line"] == "Helsinki · Rovaniemi · Kakslauttanen · Tromsø"
    assert payload["summary"]["trip_glance"]["Start"] == "Helsinki"
    assert payload["summary"]["trip_glance"]["End"] == "Tromsø"
    assert payload["summary"]["trip_glance"]["Destinations"] == "Helsinki · Rovaniemi · Kakslauttanen · Tromsø"
    assert "Onward flight and accommodation" not in html
    assert all(row["experience"] != "Onward flight and accommodation" for row in payload["summary"]["journey_arc"])
    visible_route_summary = "\n".join([payload["cover"]["destinations_line"], str(payload["summary"]["trip_glance"])])
    for term in ("your hotel", "your accommodation Private", "Rovaniemi Railway", "Ivalo"):
        assert term not in visible_route_summary


def test_journey_arc_does_not_emit_weak_accommodation_fallback_text():
    rows = _polluted_winter_rows()
    grouped = group_rows_by_day(rows)
    arc_text = "\n".join(row["experience"] for row in create_journey_arc(grouped))

    assert "Onward flight and accommodation" not in arc_text
    assert "Onward travel and accommodation" not in arc_text
    assert "Onward travel" not in arc_text


def test_plain_activity_inclusions_render_as_clean_entries_not_loose_bullets():
    html = render_inclusion_sections_inner_html([
        StructuredListSection(
            section_id="activities",
            title="Activities & experiences",
            items=(
                StructuredListItem(label="Round-trip viewpoint ticket in Tromsø - 2nd of November", source_row_ids=("viewpoint",)),
                StructuredListItem(label="Oslo Walking Tour - 5th of November", source_row_ids=("oslo",)),
            ),
        )
    ])

    assert '<div class="body-text strong-line inclusion-entry-title">Round-trip viewpoint ticket in Tromsø - 2nd of November</div>' in html
    assert '<div class="body-text strong-line inclusion-entry-title">Oslo Walking Tour - 5th of November</div>' in html
    assert '<li>Round-trip viewpoint ticket in Tromsø - 2nd of November</li>' not in html
    assert '<li>Oslo Walking Tour - 5th of November</li>' not in html
    assert 'data-source-row-ids="viewpoint"' in html
    assert 'data-source-row-ids="oslo"' in html


def test_inclusion_pagination_uses_clean_titles_and_less_aggressive_page_breaks():
    sections = [
        {
            "title": "Activities & experiences",
            "items": [f"Included activity number {index}" for index in range(1, 35)],
        },
        {
            "title": "Scenic rail & fjord journeys",
            "items": ["Norway in a Nutshell from Bergen to Oslo\nBergen Railway, Flåm Railway, fjord cruise and luggage porter service"],
        },
    ]

    pages = paginate_categorized_inclusions(sections)
    html = render_categorized_inclusions_pages("What’s included", sections)

    assert len(pages) == 1
    assert "Scenic rail &amp; fjord journeys" in html
    assert "What’s included continued" not in html
    assert "Activities &amp; experiences continued" not in html


def test_visual_editor_add_pictures_path_has_defensive_error_ui_and_bounded_image_payloads():
    frontend = _visual_editor_frontend_source()
    image_payloads = (ROOT / "visual_editor_component" / "editor_payload_images.py").read_text(encoding="utf-8")
    previews = (ROOT / "images" / "image_preview.py").read_text(encoding="utf-8")

    assert "function showEditorError" in frontend
    assert "function safeRender" in frontend
    assert "safeRender(args.payload" in frontend
    assert ".editor-error" in frontend
    assert "DAY_REPLACEMENT_OPTION_LIMIT = 8" in image_payloads
    assert "OPTION_PREVIEW_LIMIT = 2" in image_payloads
    assert "max_size=(560, 380)" in previews
    assert "quality=48" in previews
