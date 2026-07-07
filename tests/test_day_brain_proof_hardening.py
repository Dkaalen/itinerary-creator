from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.day_brain_report import build_day_brain_report
from itinerary_generation.day_copy_qa import assert_day_copy_clean
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.day_text import create_day_intro
from itinerary_parser import parse_itinerary
from scripts.smoke_hosted_generation_path import build_smoke_report
from scripts.test_groups import CHUNKED_GROUP_STAGE_SIZES, GROUPS, chunked_group_stages
from tests.fixtures.day_brain_cases import ARRIVAL_ONWARD_ROWS, FULL_LEISURE_ROWS, SAME_CITY_ACCOMMODATION_CHANGE_ROWS
from visual_editor_component.editor_payload_days import build_payload_days

REPO_ROOT = Path(__file__).resolve().parents[1]
EDGE_FIXTURE = REPO_ROOT / "tests/fixtures/real_inputs/day_brain_edge_cases.txt"


def _edge_grouped_days():
    rows = parse_itinerary(EDGE_FIXTURE.read_text(encoding="utf-8"))
    return rows, group_rows_by_day(rows)


def test_hosted_generation_smoke_exercises_client_and_agent_paths():
    report = build_smoke_report()

    assert {item["output_brand"] for item in report} == {"agent", "booknordics_customer"}
    assert all(item["ok"] for item in report)
    assert all(item["html_created"] for item in report)
    assert all(item["render_context_cached"] for item in report)
    assert all(item["render_day_count"] >= 3 for item in report)
    assert all(item["day_brain_issue_count"] == 0 for item in report)
    assert any("arrival_onward_travel" in item["day_brain_intents"] for item in report)


def test_hosted_generation_smoke_script_returns_json_success():
    completed = subprocess.run(
        [sys.executable, "scripts/smoke_hosted_generation_path.py"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert len(payload) == 2
    assert all(item["ok"] for item in payload)


def test_day_brain_debug_report_contains_all_middle_brain_layers():
    rows, grouped = _edge_grouped_days()
    report = build_day_brain_report(grouped)

    assert rows
    assert report["day_count"] >= 9
    assert report["issue_count"] == 0
    first_day = report["days"][0]
    assert {"facts", "timeline_events", "accommodation_state", "travel_load", "visit_context", "qa"}.issubset(first_day)
    assert first_day["timeline_events"]
    assert first_day["intent"] in {"arrival_stay", "arrival_onward_travel"}


def test_edge_fixture_covers_repeated_city_leisure_travel_and_accommodation_cases():
    _rows, grouped = _edge_grouped_days()
    report = build_day_brain_report(grouped)
    by_day = {day["day"]: day for day in report["days"]}

    assert by_day["Day 2"]["intent"] == "full_leisure_day"
    assert by_day["Day 7"]["intent"] == "same_city_accommodation_change"
    assert by_day["Day 8"]["facts"]["return_visit"] is True
    assert by_day["Day 4"]["travel_load"]["level"] == "overnight"
    assert by_day["Day 6"]["travel_load"]["is_travel_heavy"] is True


def test_preview_html_render_document_and_editor_payload_share_day_brain_intro():
    parsed_rows = [*ARRIVAL_ONWARD_ROWS, *SAME_CITY_ACCOMMODATION_CHANGE_ROWS, *FULL_LEISURE_ROWS]
    grouped = group_rows_by_day(parsed_rows)
    output_edits = {"output_brand": "booknordics_customer"}

    context = build_itinerary_render_context(parsed_rows, grouped, output_edits)
    html = build_itinerary_html_from_context(context)
    payload_days, generated_values = build_payload_days(
        grouped,
        output_edits,
        {},
        pictures_added=False,
        image_matches={},
        image_warnings_by_day={},
    )

    render_intros = {day.day: day.intro for day in context.render_document.days}
    payload_intros = {day["day"]: day["intro"] for day in payload_days}
    generated_intros = {day["day"]: day["intro"] for day in generated_values}

    assert render_intros
    assert render_intros == payload_intros == generated_intros
    for intro in render_intros.values():
        assert intro in html


def test_day_brain_edge_fixture_copy_is_clean_for_all_days():
    _rows, grouped = _edge_grouped_days()
    for day, rows in grouped.items():
        facts = build_day_facts(rows)
        intent = classify_day_intent(facts)
        intro = create_day_intro(rows)
        leisure = write_leisure_copy(facts, intent)
        assert_day_copy_clean(facts=facts, intent=intent, intro=intro, leisure=leisure)


def test_quality_runner_uses_smaller_timeout_safe_chunks():
    assert CHUNKED_GROUP_STAGE_SIZES["quality"] == 2
    stages = chunked_group_stages("quality", GROUPS["quality"], stage_size=CHUNKED_GROUP_STAGE_SIZES["quality"])

    assert stages
    assert all(len(paths) <= 2 for _stage, paths in stages)
    assert [path for _stage, paths in stages for path in paths] == list(GROUPS["quality"])
