from __future__ import annotations

from types import SimpleNamespace
import sys
import types

streamlit_stub = types.ModuleType("streamlit")
components_stub = types.ModuleType("streamlit.components")
components_v1_stub = types.ModuleType("streamlit.components.v1")
components_v1_stub.html = lambda *args, **kwargs: None
components_v1_stub.declare_component = lambda *args, **kwargs: (lambda **component_kwargs: None)
streamlit_stub.session_state = {}
sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", components_stub)
sys.modules.setdefault("streamlit.components.v1", components_v1_stub)

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.destination_helpers import destination_cities_for_row, is_valid_destination_city
from itinerary_generation.summaries import create_trip_glance
from visual_editor_component.editor_workflow import _normalise_journey_arc


def test_private_hotel_to_airport_does_not_create_the_destination():
    rows = [
        {
            "day": "Day 1",
            "type": "Arrival",
            "effective_type": "Arrival",
            "city": "Helsinki",
            "title": "Arrival in Helsinki",
            "details": "Arrival in Helsinki",
            "start_date": "2026-10-27",
        },
        {
            "day": "Day 11",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "title": "Private Hotel to Airport",
            "details": "Private Hotel to Airport",
            "start_date": "2026-11-06",
        },
    ]
    grouped = group_rows_by_day(rows)

    assert is_valid_destination_city("the") is False
    assert destination_cities_for_row(rows[-1]) == ["Oslo"]
    assert create_trip_glance(rows, grouped)["End"] == "Oslo"

    html = build_itinerary_html(rows, grouped, {})
    assert '<span class="cover-destination-pair">Helsinki&nbsp;·&nbsp;Oslo</span>' in html
    assert "End</td><td>the" not in html


def test_client_output_quality_gate_records_warning_during_html_generation(monkeypatch):
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Walking Tour",
            "details": "Oslo Walking Tour",
            "start_date": "2026-06-01",
        }
    ]
    grouped = group_rows_by_day(rows)

    assessment = SimpleNamespace(is_ready=False, rating="Major edit", reasons=("Forced client gate failure",))
    report = SimpleNamespace(advisor_assessment=assessment)

    monkeypatch.setattr(
        "app_modules.itinerary_render_context.evaluate_prepared_client_output_quality",
        lambda *_args, **_kwargs: report,
    )

    html = build_itinerary_html(rows, grouped, {})

    assert "preview-background" in html


def test_visual_editor_journey_arc_uses_shared_sanitizer_or_regenerates_bad_saved_rows():
    grouped = group_rows_by_day([
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Bergen",
            "title": "Hotel in Bergen",
            "details": "1 night",
        }
    ])
    saved = [{"chapter": "Bergen", "days": "1", "experience": "Flight connection"}]

    arc = _normalise_journey_arc(grouped, saved)
    arc_text = "\n".join(row["experience"] for row in arc)

    assert "Flight connection" not in arc_text
    assert "onward" not in arc_text.lower()


def test_saved_render_context_journey_arc_is_cleaned_before_pdf_contract():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Bergen",
            "title": "Hotel in Bergen",
            "details": "1 night",
        }
    ]
    output_edits = {
        "editor_draft": {
            "summary": {
                "journey_arc": [
                    {"chapter": "Bergen", "days": "1", "experience": "Flight connection"}
                ]
            }
        }
    }

    context = build_itinerary_render_context(rows, group_rows_by_day(rows), output_edits)
    summary_text = "\n".join(row["experience"] for row in context.render_document.summary.journey_arc)

    assert "Flight connection" not in summary_text
    assert "Welcome to Bergen" in summary_text
