from pathlib import Path


def test_input_page_uses_workspace_layout_not_top_stacked_buttons() -> None:
    source = Path("app_modules/input_step.py").read_text(encoding="utf-8")

    assert "render_input_hero()" in source
    assert "render_source_guidance()" in source
    assert "main_col, tool_col = st.columns([0.68, 0.32]" in source
    assert "render_calculator_entry_button()" in source
    assert "render_open_project_file_action()" in source
    assert "Paste the supplier rows first" in source


def test_input_workspace_helpers_define_clear_product_copy() -> None:
    source = Path("app_modules/input_workspace.py").read_text(encoding="utf-8")

    assert "Itinerary studio" in source
    assert "Build the travel document." in source
    assert "Start from calculator" not in source
    assert "Rows can be messy" in source
    assert "Generate itinerary" in source


def test_calculator_and_local_library_have_first_class_workspace_heroes() -> None:
    calculator = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")
    library = Path("app_modules/local_library_page.py").read_text(encoding="utf-8")

    assert "_render_calculator_hero()" in calculator
    assert "Calculator workspace" in calculator
    assert "Back to workspace" in calculator
    assert "_render_local_library_hero()" in library
    assert "Reusable rows" in library
    assert "Back to calculator" in library


def test_app_and_calculator_css_do_not_use_old_deep_green_primary() -> None:
    app_css = "\n".join(path.read_text(encoding="utf-8") for path in Path("ui").glob("style_*.py"))
    calculator_css = Path("calculator_grid_component/frontend/styles/calculator_grid.css").read_text(encoding="utf-8")
    css = app_css + "\n" + calculator_css

    forbidden = (
        "#0f6a5f",
        "#094f47",
        "rgba(15, 106, 95",
        "linear-gradient(180deg, var(--teal) 0%, var(--teal-dark) 100%)",
    )
    for marker in forbidden:
        assert marker not in css

    assert "--accent: #817769;" in app_css
    assert "--action: #2f302d;" in app_css
    assert "linear-gradient(180deg, #444640 0%, #2f302d 100%)" in calculator_css
