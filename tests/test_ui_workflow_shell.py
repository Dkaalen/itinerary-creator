from app_modules.workflow_shell import (
    build_project_metrics,
    build_workflow_steps,
    completed_step_count,
    project_route_label,
    project_title,
    workflow_progress_percent,
    workflow_steps_html,
)


def test_workflow_shell_starts_with_input_active():
    steps = build_workflow_steps({})

    assert [step.status for step in steps] == [
        "active",
        "locked",
        "locked",
        "locked",
        "locked",
        "locked",
    ]
    assert completed_step_count(steps) == 0
    assert workflow_progress_percent(steps) == 0
    assert "workflow-step-grid" in workflow_steps_html(steps)


def test_workflow_shell_reflects_generated_project_state():
    state = {
        "parsed_rows": [{"day": "Day 1", "type": "Activity", "city": "Oslo", "title": "Walk"}],
        "output_edits": {"trip_title": "Nordic City Escape", "pictures_added": True},
        "itinerary_html": "<html></html>",
        "pdf_status": "Ready",
    }

    steps = build_workflow_steps(state)

    assert [step.status for step in steps] == [
        "complete",
        "complete",
        "complete",
        "complete",
        "complete",
        "complete",
    ]
    assert workflow_progress_percent(steps) == 100
    assert project_title(state["output_edits"]) == "Nordic City Escape"


def test_project_metrics_are_consultant_facing_and_exclude_optional_items():
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
    assert project_route_label(metrics) == "Rome → Sorrento"
