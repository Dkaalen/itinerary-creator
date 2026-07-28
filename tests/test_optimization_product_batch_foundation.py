from __future__ import annotations

from app_modules.export_identity import export_signature_for_state
from app_modules.performance_telemetry import (
    begin_rerun,
    measure_timing,
    record_supabase_request,
    record_trace,
    reset_performance_telemetry,
    telemetry_snapshot,
    timing_events,
    timing_summary,
    trace_events,
)
from app_modules.presentation_language import label_for, presentation_labels
from app_modules.project_file_download_cache import cached_project_file_payload, clear_project_file_download_cache
from itinerary_generation.render_model import RenderBlock, RenderDay
from itinerary_generation.tone_presets import apply_tone_to_intro, normalize_tone_preset, tone_preset
from pdf_exporter_modules.pdf_day_renderer import day_label
from ui.render_blocks import render_block_to_html
from visual_editor_component.editor_image_payload_options import (
    metadata_first_image_option,
    metadata_first_image_options,
    option_payload_has_eager_image_data,
)


def test_performance_telemetry_records_sanitized_stage_only():
    state = {}
    reset_performance_telemetry(state)
    with measure_timing(state, "parse_input", count=3):
        pass

    events = timing_events(state)
    assert events[0]["stage"] == "parse_input"
    assert events[0]["count"] == 3
    assert "raw_text" not in events[0]


def test_app_telemetry_correlates_reruns_requests_and_safe_traces():
    state = {}

    assert begin_rerun(state) == 1
    record_trace(
        state,
        "project_selection_changed",
        selected_project_ids=("project-1", "project-2"),
    )
    record_supabase_request(
        state,
        {
            "request_id": "supabase-1",
            "method": "GET",
            "endpoint": "rest:itineraries",
            "seconds": 0.125,
            "ok": True,
            "status": 200,
            "request_bytes": 0,
            "response_bytes": 120,
        },
    )
    assert begin_rerun(state) == 2

    snapshot = telemetry_snapshot(state)
    assert snapshot["rerun_number"] == 2
    assert snapshot["request_count_total"] == 1
    assert snapshot["request_count_by_rerun"] == {"1": 1, "2": 0}
    assert any(item["event"] == "project_selection_changed" for item in trace_events(state))
    assert any(item["stage"] == "supabase_request" for item in timing_events(state))
    assert "secret" not in str(snapshot).casefold()


def test_workflow_timing_reset_preserves_app_trace_and_summary_is_bounded():
    state = {}
    begin_rerun(state)
    record_trace(state, "project_list_requested", path="management")
    with measure_timing(state, "project_list_management"):
        pass
    with measure_timing(state, "project_list_management"):
        pass

    summary = timing_summary(state)
    row = next(item for item in summary if item["stage"] == "project_list_management")
    assert row["samples"] == 2
    assert row["p50_ms"] >= 0

    reset_performance_telemetry(state)
    assert timing_events(state) == ()
    assert any(item["event"] == "project_list_requested" for item in trace_events(state))
    assert telemetry_snapshot(state)["rerun_number"] == 1


def test_metadata_first_image_options_strip_eager_base64_fields():
    option = metadata_first_image_option(
        {
            "path": "/image_bank/Oslo/fjord.jpg",
            "name": "fjord.jpg",
            "preview_data_uri": "data:image/jpeg;base64,abc",
            "data_uri": "data:image/jpeg;base64,def",
            "score": 98,
        }
    )
    assert option == {"path": "/image_bank/Oslo/fjord.jpg", "name": "fjord.jpg", "label": "fjord.jpg", "score": 98}
    assert not option_payload_has_eager_image_data(option)
    assert metadata_first_image_options([option], limit=1)[0]["path"].endswith("fjord.jpg")


def test_export_signature_tracks_image_state_not_only_preview_signature():
    base_state = {"preview_signature": "abc", "output_edits": {"day_images": {"Day 1": {"path": "a.jpg"}}}}
    changed_state = {"preview_signature": "abc", "output_edits": {"day_images": {"Day 1": {"path": "b.jpg"}}}}
    assert export_signature_for_state(base_state) != export_signature_for_state(changed_state)


def test_presentation_language_labels_feed_preview_and_pdf_render_helpers():
    labels = presentation_labels("de").labels
    block = RenderBlock(kind="activity", includes=["Guide"], description="Walk", labels=labels)
    html = render_block_to_html(block)["html"]
    assert "Bei diesem Erlebnis inbegriffen" in html
    assert "Beschreibung" in html

    day = RenderDay(day="Day 1", number="1", city="Oslo", title="Oslo", intro="Intro", labels=labels)
    assert day_label(day).startswith("TAG 1")
    assert label_for({"presentation_language": "fr"}, "whats_included") == "Ce qui est inclus"


def test_tone_presets_are_controlled_and_apply_only_to_text():
    assert normalize_tone_preset("Family Friendly") == "family_friendly"
    assert tone_preset("minimal_agent").detail_level == "Standard client itinerary"
    assert apply_tone_to_intro("Explore Oslo.", "adventure_focused").startswith("Set out for an active day")


def test_project_file_download_cache_is_session_local_by_signature():
    state = {}
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"data": b"{}"}

    assert cached_project_file_payload(state, "sig-1", builder) == {"data": b"{}"}
    assert cached_project_file_payload(state, "sig-1", builder) == {"data": b"{}"}
    assert calls["count"] == 1
    assert cached_project_file_payload(state, "sig-2", builder) == {"data": b"{}"}
    assert calls["count"] == 2
    clear_project_file_download_cache(state)
    assert "_project_file_download_cache" not in state
