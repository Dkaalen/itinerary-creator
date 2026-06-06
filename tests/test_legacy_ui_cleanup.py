from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dead_sidebar_workflow_is_reduced_to_safe_shim() -> None:
    text = (ROOT / "app_modules" / "sidebar.py").read_text(encoding="utf-8")

    assert "Compatibility shim" in text
    assert len(text.splitlines()) <= 40
    assert "st.sidebar" not in text
    assert "apply_rich_writing_to_all_days" not in text


def test_duplicate_visual_editor_streamlit_styles_are_removed_from_shim() -> None:
    text = (ROOT / "visual_editor_component" / "ui" / "styles.py").read_text(encoding="utf-8")

    assert "Compatibility shim" in text
    assert len(text.splitlines()) <= 5
    assert "div[data-testid=\"stSidebar\"]" not in text
    assert "from ui.styles import apply_global_styles" in text


def test_visual_editor_app_module_shims_stay_small() -> None:
    shim_paths = [
        ROOT / "visual_editor_component" / "app_modules" / "main_view.py",
        ROOT / "visual_editor_component" / "app_modules" / "export_step.py",
        ROOT / "visual_editor_component" / "app_modules" / "workflow_shell.py",
    ]

    for path in shim_paths:
        text = path.read_text(encoding="utf-8")
        assert "Compatibility shim" in text
        assert len(text.splitlines()) <= 40
        assert "st.sidebar" not in text
