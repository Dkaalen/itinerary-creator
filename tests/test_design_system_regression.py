from __future__ import annotations

import ast
from pathlib import Path


def _text(relative_path: str) -> str:
    return Path(relative_path).read_text(encoding="utf-8")


def _contains(relative_path: str, token: str) -> bool:
    return token in _text(relative_path)


def _omits(relative_path: str, token: str) -> bool:
    return token not in _text(relative_path)


def _python_calls(relative_path: str) -> set[str]:
    tree = ast.parse(_text(relative_path))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    return calls


def test_input_page_is_debloated_workspace_not_card_dashboard() -> None:
    calls = _python_calls("app_modules/input_step.py")

    assert {"render_input_toolbar", "render_input_header", "render_source_label"}.issubset(calls)
    assert {"render_input_hero", "render_source_guidance", "render_generation_action_bar"}.isdisjoint(calls)
    assert {"render_presentation_language_selector", "render_tone_preset_selector"}.isdisjoint(calls)
    assert {"open_calculator_page", "open_local_library_page", "render_open_project_file_action"}.issubset(calls)
    assert _contains("app_modules/input_step.py", "Paste the supplier rows first")
    assert _omits("app_modules/input_step.py", "main_col, tool_col")


def test_input_workspace_helpers_remove_landing_page_bloat() -> None:
    required_tokens = {
        "Itinerary Studio",
        "By Booknordics.com",
        "studio-brand-static",
        "BOOKNORDICS_SYMBOL_PATH",
        "New itinerary",
        "Supplier rows",
    }
    retired_tokens = {
        "Build the travel document.",
        "Suggested flow",
        "Alternate start",
        "Rows can be messy",
        "Generate itinerary",
    }

    assert all(_contains("app_modules/input_workspace.py", token) for token in required_tokens)
    assert all(_omits("app_modules/input_workspace.py", token) for token in retired_tokens)
    assert _omits("app_modules/input_workspace.py", "href=")


def test_calculator_and_local_library_have_plain_workspace_headers() -> None:
    calculator_calls = _python_calls("app_modules/calculator_page.py")
    library_calls = _python_calls("app_modules/local_library_page.py")

    assert "_render_calculator_header" in calculator_calls
    assert _contains("app_modules/calculator_page.py", "Calculator workspace")
    assert _contains("app_modules/calculator_page.py", "<h1>Calculator</h1>")
    assert _omits("app_modules/calculator_page.py", "Price the itinerary before it becomes a document")
    assert _contains("app_modules/calculator_page.py", "render_back_to_main_page_button")
    assert _contains("app_modules/calculator_navigation.py", "Back to main page")
    assert _contains("calculator_grid_component/frontend/js/calculator_grid_toolbar_render.js", "Local Library")
    assert "_render_local_library_header" in library_calls
    assert _contains("app_modules/local_library_page.py", "Reusable rows")
    assert _contains("app_modules/local_library_page.py", "<h1>Local Library</h1>")
    assert _omits("app_modules/local_library_page.py", "Keep common services ready")
    assert _contains("app_modules/local_library_page.py", "Back to itinerary calculator")


def test_app_and_calculator_css_do_not_use_old_deep_green_or_dark_primary() -> None:
    app_css = "\n".join(path.read_text(encoding="utf-8") for path in Path("ui").glob("style_*.py"))
    calculator_css = _text("calculator_grid_component/frontend/styles/calculator_grid.css")
    css = app_css + "\n" + calculator_css
    forbidden = (
        "#0f6a5f",
        "#094f47",
        "rgba(15, 106, 95",
        "linear-gradient(180deg, var(--teal) 0%, var(--teal-dark) 100%)",
        "linear-gradient(180deg, var(--sumi-2) 0%, var(--action) 100%)",
        "linear-gradient(180deg, #444640 0%, #2f302d 100%)",
    )

    assert all(marker not in css for marker in forbidden)
    assert "--accent: #9a8f7f;" in app_css
    assert "--primary-action: #233446;" in app_css
    assert ".calc-btn.primary { background: #233446;" in calculator_css
