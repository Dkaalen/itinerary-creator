import json
import sys
import types
from pathlib import Path

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

from app_modules.itinerary_html import build_itinerary_html
from itinerary_generation.editable_draft import normalise_editable_draft
from ui.day_page_sections import render_day_section
from visual_editor_component.editor_workflow import apply_visual_editor_result, build_visual_editor_payload


def _visual_editor_frontend_source():
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


def test_editor_payload_exposes_typed_draft_contract():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Tromsø",
            "title": "Arctic Photo Tour",
            "client_description": "Generated supplier details",
        }
    ]

    payload = build_visual_editor_payload(
        rows,
        {"Day 1": rows},
        {"days": {}, "important_travel_notes_text": "Bring ID", "pictures_added": False, "draft_id": "draft-1"},
    )

    assert payload["meta"]["draft_schema_version"] == 3
    draft = payload["editor_draft"]
    assert draft["schema_version"] == 3
    assert draft["days"][0]["day_id"] == "Day 1"
    assert draft["days"][0]["blocks"][0]["kind"] == "day_content"
    assert draft["final_sections"][-1]["section_id"] == "important_travel_notes"


def test_visual_editor_save_prefers_typed_draft_but_mirrors_legacy_for_pdf():
    output_edits = {"days": {}}
    result = json.dumps(
        {
            "editor_draft": {
                "schema_version": 3,
                "cover": {"trip_title": "Typed title", "destinations_line": "Oslo\nBergen"},
                "summary": {},
                "days": [
                    {
                        "day_id": "Day 1",
                        "title": "Typed Day",
                        "city": "Oslo",
                        "intro": "Typed intro",
                        "blocks": [{"block_id": "main", "kind": "day_content", "content_html": "<div>Typed day block</div>"}],
                    }
                ],
                "final_sections": [
                    {
                        "section_id": "whats_not_included",
                        "title": "What's not included",
                        "content_html": "<ul><li>Typed exclusion</li></ul>",
                    }
                ],
                "workflow": {"pictures_added": False},
            }
        }
    )

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["editor_draft"]["schema_version"] == 3
    assert output_edits["trip_title"] == "Typed title"
    assert output_edits["destinations_line"] == "Oslo · Bergen"
    assert output_edits["days"]["Day 1"]["blocks_html"] == "<div>Typed day block</div>"
    assert output_edits["whats_not_included_html"] == "<ul><li>Typed exclusion</li></ul>"


def test_rendering_can_consume_typed_draft_without_legacy_day_html():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Generated Activity",
            "client_description": "Generated details",
        }
    ]
    output_edits = {
        "days": {},
        "editor_draft": normalise_editable_draft(
            {
                "days": [
                    {
                        "day": "Day 1",
                        "title": "Typed Day",
                        "city": "Oslo",
                        "intro": "Typed intro",
                        "blocks_html": "<div>Typed-only block</div>",
                    }
                ]
            }
        ),
    }

    html = render_day_section("Day 1", rows, output_edits)

    assert "Typed-only block" in html
    assert "Generated details" not in html


def test_full_preview_can_consume_typed_final_sections_without_legacy_keys():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Generated Activity",
        }
    ]
    output_edits = {
        "days": {},
        "editor_draft": normalise_editable_draft(
            {
                "cover": {"trip_title": "Typed Cover"},
                "final_pages": {
                    "whats_included_pages_html": [{"html": "<div>Typed included page</div>"}],
                    "whats_not_included_html": "<ul><li>Typed excluded page</li></ul>",
                    "important_travel_notes_text": "Typed notes",
                },
            }
        ),
    }

    html = build_itinerary_html(rows, {"Day 1": rows}, output_edits)

    assert "Typed Cover" in html
    assert "Typed included page" in html
    assert "Typed excluded page" in html
    assert "Typed notes" in html


def test_frontend_builds_typed_draft_before_commit():
    editor_html = _visual_editor_frontend_source()

    assert "function buildEditableDraftFromPayload" in editor_html
    assert "payload.editor_draft = buildEditableDraftFromPayload(payload)" in editor_html
    assert "full.editor_draft = buildEditableDraftFromPayload(full)" in editor_html


def test_empty_typed_final_section_suppresses_stale_legacy_inclusions_html():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Generated Activity",
            "commercial_status": "included",
        }
    ]
    output_edits = {
        "days": {},
        "whats_included_html": "<div>Stale legacy inclusion</div>",
        "editor_draft": normalise_editable_draft(
            {
                "final_sections": [
                    {
                        "section_id": "whats_included",
                        "title": "What's included",
                        "pages": [],
                        "content_html": "",
                        "text": "",
                    }
                ]
            }
        ),
    }

    html = build_itinerary_html(rows, {"Day 1": rows}, output_edits)

    assert "Stale legacy inclusion" not in html


def test_empty_typed_final_section_suppresses_stale_legacy_exclusions_html():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Generated Activity",
        }
    ]
    output_edits = {
        "days": {},
        "whats_not_included_html": "<div>Stale legacy exclusion</div>",
        "editor_draft": normalise_editable_draft(
            {
                "final_sections": [
                    {
                        "section_id": "whats_not_included",
                        "title": "What's not included",
                        "pages": [],
                        "content_html": "",
                        "text": "",
                    }
                ]
            }
        ),
    }

    html = build_itinerary_html(rows, {"Day 1": rows}, output_edits)

    assert "Stale legacy exclusion" not in html
