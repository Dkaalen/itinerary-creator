from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dead_streamlit_editor_modules_are_removed() -> None:
    removed_paths = [
        ROOT / "app_modules" / "sidebar.py",
        ROOT / "app_modules" / "output_editor.py",
        ROOT / "app_modules" / "image_review.py",
    ]

    for path in removed_paths:
        assert not path.exists(), f"legacy module should stay removed: {path}"


def test_removed_streamlit_editor_modules_are_not_imported() -> None:
    searchable_roots = [
        ROOT / "app.py",
        ROOT / "app_modules",
        ROOT / "visual_editor_component",
        ROOT / "ui",
    ]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in searchable_roots
        for path in ([root] if root.is_file() else root.rglob("*.py"))
        if path.name not in {"__pycache__"}
    )

    assert "app_modules.output_editor" not in text
    assert "app_modules.image_review" not in text
    assert "app_modules.sidebar" not in text


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


def test_legacy_frontend_bullet_tools_are_removed() -> None:
    frontend_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "visual_editor_component" / "frontend" / "js").glob("*.js")
    )

    assert "addBullet" not in frontend_text
    assert "deleteBullet" not in frontend_text
    assert "moveBullet" not in frontend_text
    assert "addBulletBtn" not in frontend_text
    assert "moveBulletUpBtn" not in frontend_text
