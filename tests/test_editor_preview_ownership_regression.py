import json
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

from app_modules.itinerary_html import build_itinerary_html
from itinerary_generation.editable_draft import merge_editable_drafts, normalise_editable_draft
from visual_editor_component.editor_workflow import apply_visual_editor_result, build_visual_editor_payload


def _existing_draft():
    return normalise_editable_draft(
        {
            "cover": {"trip_title": "Stored title", "destinations_line": "Oslo · Bergen"},
            "days": [
                {
                    "day": "Day 1",
                    "title": "Stored Day 1",
                    "city": "Oslo",
                    "intro": "Stored intro 1",
                    "blocks_html": "<div>Stored Day 1 block</div>",
                },
                {
                    "day": "Day 2",
                    "title": "Stored Day 2",
                    "city": "Bergen",
                    "intro": "Stored intro 2",
                    "blocks_html": "<div>Stored Day 2 block</div>",
                },
            ],
            "final_pages": {
                "whats_included_pages_html": [
                    {"html": "<div>Stored included page 1</div>"},
                    {"html": "<div>Stored included page 2</div>"},
                ],
                "whats_not_included_html": "<ul><li>Stored exclusion</li></ul>",
                "important_travel_notes_text": "Stored notes",
            },
            "workflow": {"pictures_added": True},
        }
    )


def test_partial_typed_editor_draft_merges_without_losing_untouched_days_or_final_sections():
    existing = _existing_draft()
    incoming = normalise_editable_draft(
        {
            "cover": {"trip_title": "Edited title"},
            "days": [
                {
                    "day": "Day 2",
                    "title": "Edited Day 2",
                    "city": "Bergen",
                    "intro": "Edited intro 2",
                    "blocks_html": "<div>Edited Day 2 block</div>",
                }
            ],
        }
    )

    merged = merge_editable_drafts(existing, incoming)

    assert merged["cover"]["trip_title"] == "Edited title"
    assert merged["cover"]["destinations_line"] == "Oslo · Bergen"
    assert [day["day_id"] for day in merged["days"]] == ["Day 1", "Day 2"]
    assert merged["days"][0]["blocks"][0]["content_html"] == "<div>Stored Day 1 block</div>"
    assert merged["days"][1]["title"] == "Edited Day 2"
    included = next(section for section in merged["final_sections"] if section["section_id"] == "whats_included")
    assert [page["content_html"] for page in included["pages"]] == [
        "<div>Stored included page 1</div>",
        "<div>Stored included page 2</div>",
    ]
    assert merged["workflow"]["pictures_added"] is True


def test_visual_editor_partial_save_preserves_existing_typed_draft_source_of_truth():
    output_edits = {"days": {}, "editor_draft": _existing_draft()}
    result = json.dumps(
        {
            "cover": {"trip_title": "Edited title"},
            "summary": {},
            "days": [
                {
                    "day": "Day 2",
                    "title": "Edited Day 2",
                    "blocks_html": "<div>Edited Day 2 block</div>",
                }
            ],
            "final_pages": {},
            "editor_draft": normalise_editable_draft(
                {
                    "cover": {"trip_title": "Edited title"},
                    "days": [
                        {
                            "day": "Day 2",
                            "title": "Edited Day 2",
                            "blocks_html": "<div>Edited Day 2 block</div>",
                        }
                    ],
                }
            ),
        }
    )

    assert apply_visual_editor_result(result, output_edits)

    draft = output_edits["editor_draft"]
    assert [day["day_id"] for day in draft["days"]] == ["Day 1", "Day 2"]
    assert output_edits["days"]["Day 1"]["blocks_html"] == "<div>Stored Day 1 block</div>"
    assert output_edits["days"]["Day 2"]["blocks_html"] == "<div>Edited Day 2 block</div>"
    assert output_edits["whats_included_pages_html"] == [
        "<div>Stored included page 1</div>",
        "<div>Stored included page 2</div>",
    ]
    assert output_edits["whats_not_included_html"] == "<ul><li>Stored exclusion</li></ul>"
    assert output_edits["important_travel_notes_text"] == "Stored notes"


def test_preview_and_editor_payload_keep_merged_typed_day_and_final_page_edits_visible():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Generated One"},
        {"type": "Activity", "effective_type": "Activity", "day": "Day 2", "city": "Bergen", "title": "Generated Two"},
    ]
    grouped = {"Day 1": [rows[0]], "Day 2": [rows[1]]}
    output_edits = {"days": {}, "editor_draft": _existing_draft(), "pictures_added": False}

    html = build_itinerary_html(rows, grouped, output_edits)
    payload = build_visual_editor_payload(rows, grouped, output_edits)

    assert "Stored Day 1 block" in html
    assert "Stored Day 2 block" in html
    assert "Stored included page 1" in html
    assert payload["days"][0]["blocks_html"] == "<div>Stored Day 1 block</div>"
    assert payload["days"][1]["blocks_html"] == "<div>Stored Day 2 block</div>"
    assert [page["html"] for page in payload["final_pages"]["whats_included_pages_html"]][:2] == [
        "<div>Stored included page 1</div>",
        "<div>Stored included page 2</div>",
    ]
