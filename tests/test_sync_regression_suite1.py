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

from itinerary_generation.day_text import create_day_intro
from itinerary_generation.editable_draft import merge_editable_drafts, normalise_editable_draft
from itinerary_generation.generated_ownership import day_source_signature
from itinerary_generation.render_document_builder import build_render_document
from pdf_exporter_modules.typed_exporter import render_document_requires_html_fallback
from visual_editor_component.editor_workflow import apply_visual_editor_result, build_visual_editor_payload


def _lysefjord_rows():
    return [
        {
            "row_id": "r1",
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 6",
            "city": "Stavanger",
            "title": "Lysefjord & Preikestolen Fjord Cruise by electric boat",
            "details": "Sail through Lysefjord below Preikestolen on an electric boat.",
        }
    ]


def _bergen_nutshell_rows():
    return [
        {
            "row_id": "n1",
            "type": "Train",
            "effective_type": "Train",
            "day": "Day 9",
            "city": "Oslo",
            "title": "Norway in a Nutshell from Bergen to Oslo",
            "details": "Bergen Railway, Nærøyfjord cruise, Flåm Railway and coach connections.",
        }
    ]


def test_stale_generated_output_edits_intro_refreshes_in_preview_and_pdf_context():
    rows = _lysefjord_rows()
    grouped = {"Day 6": rows}
    stale_intro = "Sail from Stavanger on Lysefjord & Preikestolen Fjord Cruise, with fjord scenery, coastal landmarks and time on the water shaping the day."
    output_edits = {"days": {"Day 6": {"intro": stale_intro}}, "pictures_added": False}

    payload = build_visual_editor_payload(rows, grouped, output_edits)
    render_document = build_render_document(rows, grouped, output_edits=output_edits)

    assert payload["days"][0]["intro"] == render_document.days[0].intro
    assert "The day centres on Lysefjord" in payload["days"][0]["intro"]
    assert "Sail from Stavanger" not in payload["days"][0]["intro"]


def test_manual_intro_override_survives_generator_refresh():
    rows = _lysefjord_rows()
    grouped = {"Day 6": rows}
    output_edits = {
        "days": {
            "Day 6": {
                "intro": "Custom agency-written Lysefjord intro.",
                "intro_manual_override": True,
                "intro_generated_value": create_day_intro(rows, detail_level="Rich descriptive"),
                "intro_source_signature": day_source_signature(rows),
            }
        },
        "pictures_added": False,
    }

    payload = build_visual_editor_payload(rows, grouped, output_edits)
    render_document = build_render_document(rows, grouped, output_edits=output_edits)

    assert payload["days"][0]["intro"] == "Custom agency-written Lysefjord intro."
    assert render_document.days[0].intro == "Custom agency-written Lysefjord intro."


def test_editor_draft_stale_generated_intro_refreshes_but_manual_intro_stays():
    rows = _bergen_nutshell_rows()
    grouped = {"Day 9": rows}
    stale_draft = normalise_editable_draft(
        {
            "days": [
                {
                    "day": "Day 9",
                    "intro": "The journey continues towards Oslo, with the Norway in a Nutshell route arranged as a clear and scenic travel day.",
                    "intro_manual_override": False,
                }
            ]
        }
    )
    output_edits = {"days": {}, "editor_draft": stale_draft, "pictures_added": False}

    payload = build_visual_editor_payload(rows, grouped, output_edits)
    render_document = build_render_document(rows, grouped, output_edits=output_edits)

    assert payload["days"][0]["intro"] == render_document.days[0].intro
    assert "signature scenic journey" in payload["days"][0]["intro"] or "rail, coach and fjord-cruise" in payload["days"][0]["intro"]
    assert "The journey continues" not in payload["days"][0]["intro"]


def test_image_only_autosave_does_not_blank_or_manualize_day_text():
    existing = normalise_editable_draft(
        {
            "days": [
                {
                    "day": "Day 1",
                    "title": "Generated title",
                    "city": "Oslo",
                    "intro": "Generated intro",
                    "intro_manual_override": False,
                    "blocks_html": "<div>Generated block</div>",
                    "blocks_manual_override": False,
                }
            ]
        }
    )
    incoming = normalise_editable_draft(
        {
            "days": [
                {
                    "day": "Day 1",
                    "image": {"mode": "manual", "crop_focus": "center"},
                }
            ]
        }
    )

    merged = merge_editable_drafts(existing, incoming)
    day = merged["days"][0]

    assert day["intro"] == "Generated intro"
    assert day["intro_manual_override"] is False
    assert day["blocks"][0]["content_html"] == "<div>Generated block</div>"
    assert day["blocks_manual_override"] is False
    assert day["image"]["mode"] == "manual"


def test_visual_editor_intro_edit_marks_manual_but_image_edit_does_not():
    output_edits = {"days": {}}
    assert apply_visual_editor_result(
        json.dumps(
            {
                "days": [
                    {
                        "day": "Day 1",
                        "intro": "Manual intro from canvas",
                        "intro_manual_override": True,
                    }
                ]
            }
        ),
        output_edits,
    )
    assert output_edits["days"]["Day 1"]["intro_manual_override"] is True

    output_edits = {"days": {"Day 1": {"intro": "Generated intro", "intro_manual_override": False}}}
    assert apply_visual_editor_result(
        json.dumps({"days": [{"day": "Day 1", "image": {"mode": "none"}}]}),
        output_edits,
    )
    assert output_edits["days"]["Day 1"]["intro"] == "Generated intro"
    assert output_edits["days"]["Day 1"]["intro_manual_override"] is False


def test_generated_blocks_html_does_not_force_pdf_fallback_but_manual_blocks_do():
    rows = _lysefjord_rows()
    grouped = {"Day 6": rows}
    render_document = build_render_document(rows, grouped, output_edits={"days": {}})

    generated_state = {
        "days": {
            "Day 6": {
                "blocks_html": "<div class='content-block'><div class='body-text'>Old generated mirror</div></div>",
                "blocks_manual_override": False,
            }
        }
    }
    manual_state = {
        "days": {
            "Day 6": {
                "blocks_html": "<div><p>Manual rewritten body</p></div>",
                "blocks_manual_override": True,
            }
        }
    }

    assert render_document_requires_html_fallback(render_document, generated_state) is False
    assert render_document_requires_html_fallback(render_document, manual_state) is True


def test_copy_rules_keep_lysefjord_and_oslofjord_separate():
    lysefjord_intro = create_day_intro(_lysefjord_rows(), detail_level="Rich descriptive")
    oslo_rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 2",
            "city": "Oslo",
            "title": "Oslofjord Sightseeing Cruise onboard Electric Boat",
            "details": "Meet by the TROLLCRUISE sign.",
        }
    ]
    oslo_intro = create_day_intro(oslo_rows, detail_level="Rich descriptive")

    assert "The day centres on Lysefjord" in lysefjord_intro
    assert "Begin with Oslo from the water" in oslo_intro
    assert "Begin with Oslo" not in lysefjord_intro
