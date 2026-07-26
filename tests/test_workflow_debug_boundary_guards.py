from pathlib import Path


APP = Path("app_modules")


def _read(relative: str) -> str:
    return (APP / relative).read_text(encoding="utf-8")


def test_main_view_is_stage_router_not_workflow_dumping_ground():
    source = _read("main_view.py")

    assert "def render_app" in source
    assert "resolve_active_route" in source
    assert "_load_route_renderer" in source
    assert "route_spec_for" in source

    forbidden = [
        "render_structured_input_review_panel",
        "render_parser_diagnostics_panel",
        "render_itinerary_health_report_panel",
        "st.dataframe",
        "Show parser/debug panels",
    ]
    for marker in forbidden:
        assert marker not in source


def test_normal_generation_messages_are_debug_only():
    source = _read("generation_messages.py")

    assert "def render_generation_messages" in source
    assert "if not is_debug_mode(state):" in source
    assert "render_structured_input_review_panel" in source
    assert source.index("if not is_debug_mode(state):") < source.index("render_structured_input_review_panel")


def test_debug_tools_have_single_real_boundary():
    source = _read("debug_tools.py")

    assert "if not is_debug_mode(st.session_state):" in source
    assert "render_parser_diagnostics_panel" in source
    assert "render_itinerary_health_report_panel" in source
    assert "Show parser/debug panels" not in source


def test_workflow_actions_are_split_by_responsibility():
    compatibility = _read("workflow_actions.py")

    assert "from app_modules.generation_action import generate_itinerary" in compatibility
    assert "from app_modules.project_load_action import load_project" in compatibility
    assert "from app_modules.image_stage_action import enter_picture_stage, retry_image_bank_connection" in compatibility
    assert "from app_modules.export_stage_action import enter_export_stage" in compatibility
    assert "def generate_itinerary" not in compatibility
    assert "def load_project" not in compatibility

    assert "def generate_itinerary" in _read("generation_action.py")
    assert "def load_project" in _read("project_load_action.py")
    assert "def enter_picture_stage" in _read("image_stage_action.py")
    assert "def enter_export_stage" in _read("export_stage_action.py")
