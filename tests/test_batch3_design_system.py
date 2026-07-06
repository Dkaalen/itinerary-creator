from pathlib import Path


def test_input_page_is_debloated_workspace_not_card_dashboard() -> None:
    source = Path("app_modules/input_step.py").read_text(encoding="utf-8")

    assert "render_input_toolbar()" in source
    assert "render_input_header()" in source
    assert "render_source_label()" in source
    assert "render_input_hero()" not in source
    assert "render_source_guidance()" not in source
    assert "render_generation_action_bar" not in source
    assert "main_col, tool_col" not in source
    assert "render_presentation_language_selector" not in source
    assert "render_tone_preset_selector" not in source
    assert "open_calculator_page(st.session_state)" in source
    assert "open_local_library_page(st.session_state)" in source
    assert "render_open_project_file_action()" in source
    assert "Paste the supplier rows first" in source


def test_input_workspace_helpers_remove_landing_page_bloat() -> None:
    source = Path("app_modules/input_workspace.py").read_text(encoding="utf-8")

    assert "Itinerary Studio" in source
    assert "By Booknordics.com" in source
    assert "studio-brand-static" in source
    assert "href=" not in source
    assert "BOOKNORDICS_SYMBOL_PATH" in source
    assert "New itinerary" in source
    assert "Supplier rows" in source
    assert "Build the travel document." not in source
    assert "Suggested flow" not in source
    assert "Alternate start" not in source
    assert "Rows can be messy" not in source
    assert "Generate itinerary" not in source


def test_calculator_and_local_library_have_plain_workspace_headers() -> None:
    calculator = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")
    library = Path("app_modules/local_library_page.py").read_text(encoding="utf-8")

    assert "_render_calculator_header()" in calculator
    assert "Calculator workspace" in calculator
    assert "<h1>Calculator</h1>" in calculator
    assert "Price the itinerary before it becomes a document" not in calculator
    assert "Back to workspace" in calculator
    assert "Manage Local Library" in calculator
    assert "_render_local_library_header()" in library
    assert "Reusable rows" in library
    assert "<h1>Local Library</h1>" in library
    assert "Keep common services ready" not in library
    assert "Back to itinerary calculator" in library


def test_app_and_calculator_css_do_not_use_old_deep_green_or_dark_primary() -> None:
    app_css = "\n".join(path.read_text(encoding="utf-8") for path in Path("ui").glob("style_*.py"))
    calculator_css = Path("calculator_grid_component/frontend/styles/calculator_grid.css").read_text(encoding="utf-8")
    css = app_css + "\n" + calculator_css

    forbidden = (
        "#0f6a5f",
        "#094f47",
        "rgba(15, 106, 95",
        "linear-gradient(180deg, var(--teal) 0%, var(--teal-dark) 100%)",
        "linear-gradient(180deg, var(--sumi-2) 0%, var(--action) 100%)",
        "linear-gradient(180deg, #444640 0%, #2f302d 100%)",
    )
    for marker in forbidden:
        assert marker not in css

    assert "--accent: #9a8f7f;" in app_css
    assert "--primary-action: #233446;" in app_css
    assert ".calc-btn.primary { background: #233446;" in calculator_css
