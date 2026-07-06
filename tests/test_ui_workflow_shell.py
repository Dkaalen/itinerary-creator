from __future__ import annotations

from pathlib import Path

from app_modules.workflow_shell import build_project_metrics, project_next_action_label, project_route_label, project_title


ROOT = Path(__file__).resolve().parents[1]


def test_project_metrics_are_header_facing_and_exclude_optional_items() -> None:
    rows = [
        {"day": "Day 1", "type": "Hotel", "city": "Rome", "title": "Hotel"},
        {"day": "Day 1", "type": "Activity", "city": "Rome", "title": "Walking Tour"},
        {"day": "Day 2", "type": "Transfer", "city": "Sorrento", "title": "Private Transfer"},
        {"day": "Day 2", "type": "Activity", "city": "Sorrento", "title": "Optional Wine", "is_optional": True},
    ]

    metrics = build_project_metrics(rows, {"pictures_added": False})

    assert metrics["days"] == 2
    assert metrics["destinations"] == 2
    assert metrics["activities"] == 1
    assert metrics["hotels"] == 1
    assert metrics["transfers"] == 1
    assert metrics["optional_rows"] == 1
    assert metrics["pictures_added"] is False
    assert project_route_label(metrics) == "Rome → Sorrento"


def test_project_header_copy_stays_direct_and_not_review_step_based() -> None:
    assert project_title({"trip_title": "Nordic City Escape"}) == "Nordic City Escape"
    assert project_title({}, "Create itinerary") == "Create itinerary"
    assert project_route_label({"destination_names": ["Oslo", "Bergen", "Flåm", "Ålesund"]}) == "Oslo → Bergen → Flåm + 1 more"
    assert project_next_action_label("edit", {"pictures_added": False}) == "Next · apply changes"
    assert project_next_action_label("pictures", {"pictures_added": True}) == "Next · review images"
    assert project_next_action_label("export", {"pictures_added": True}) == "Next · create PDF"

    source = (ROOT / "app_modules" / "workflow_shell.py").read_text(encoding="utf-8")
    stale_step_copy = ("Structure Review", "Client Text", "Image Review", "workflow_steps_html", "WorkflowStep")
    for marker in stale_step_copy:
        assert marker not in source
