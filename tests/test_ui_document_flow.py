from pathlib import Path

from images.replacement_options import list_replacement_image_options_for_rows


def test_main_view_uses_simple_document_flow_without_old_step_accordions():
    source = Path("app_modules/main_view.py").read_text()

    assert 'FLOW_STAGES = ("input", "edit", "pictures", "export")' in source

    assert "render_sidebar_controls" not in source
    assert "render_workflow_overview" not in source
    assert "1 — Import supplier rows" not in source
    assert "3 — Add and approve pictures" not in source
    assert "Generate Itinerary" in source
    assert "Add pictures" in source
    assert "Create PDF" in source or "render_export_step" in source


def test_replacement_options_do_not_show_default_only_bank(tmp_path):
    default_dir = tmp_path / "image_bank" / "Default"
    default_dir.mkdir(parents=True)
    (default_dir / "Default_Summer_Fjord_01.webp").write_bytes(b"placeholder")

    options = list_replacement_image_options_for_rows(
        "Day 1",
        [{"day": "Day 1", "city": "Bergen", "title": "Walking tour"}],
        image_bank_scan_paths=[tmp_path / "image_bank"],
    )

    assert options == []
