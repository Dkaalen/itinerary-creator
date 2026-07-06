from __future__ import annotations

from pathlib import Path


def test_local_library_page_is_routed_from_main_view() -> None:
    main_view = Path("app_modules/main_view.py").read_text(encoding="utf-8")

    assert "local_library_page_is_active" in main_view
    assert "render_local_library_page(app_version)" in main_view


def test_calculator_page_exposes_manage_local_library_button() -> None:
    calculator_page = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "Manage Local Library" in calculator_page
    assert "open_local_library_page" in calculator_page


def test_local_library_page_has_required_management_actions() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "app_modules/local_library_page.py",
            "app_modules/local_library_editor_form.py",
            "app_modules/local_library_status_ui.py",
        )
    )

    assert "Back to itinerary calculator" in sources
    assert "Save Local Library row" in sources
    assert "Remove Local Library row" in sources
    assert "read_only" in sources
    assert "Google Sheets" in sources


def test_local_library_page_is_split_by_responsibility() -> None:
    page = Path("app_modules/local_library_page.py").read_text(encoding="utf-8")

    assert "render_local_library_source_status" in page
    assert "render_local_library_row_selector" in page
    assert "render_local_library_editor" in page
    assert "LocalLibraryStore" not in page
    assert "st.form" not in page
