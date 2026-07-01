from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PRODUCTION_FILES = (
    ROOT / "app_modules/main_view.py",
    ROOT / "app_modules/preview_step.py",
    ROOT / "visual_editor_component/editor_payload_builder.py",
    *(ROOT / "visual_editor_component/frontend/js").glob("*.js"),
)

LEGACY_MARKERS = (
    "breadcrumbs",
    "source-contract",
    "Compatibility loader",
    "Migration breadcrumbs",
    "Legacy source-contract",
    "Legacy review navigation",
)


def test_patch_40_removes_legacy_breadcrumb_markers_from_production_sources():
    hits = []
    for path in PRODUCTION_FILES:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for marker in LEGACY_MARKERS:
            if marker in source:
                hits.append(f"{path.relative_to(ROOT)}: {marker}")

    assert hits == []


def test_patch_40_removes_empty_style_preset_shim_without_breaking_asset_loading():
    index_html = (ROOT / "visual_editor_component/frontend/index.html").read_text(encoding="utf-8")
    asset_loader = (ROOT / "visual_editor_component/frontend/js/editor_assets.js").read_text(encoding="utf-8")

    assert not (ROOT / "visual_editor_component/frontend/js/style_presets.js").exists()
    assert 'src="js/style_presets.js"' not in index_html
    assert "style_preset_data.js" in asset_loader
    assert "style_preset_lookup.js" in asset_loader
    assert "editor_block_templates.js" in asset_loader


def test_patch_40_removes_empty_legacy_preview_hook():
    preview_step = (ROOT / "app_modules/preview_step.py").read_text(encoding="utf-8")
    main_view = (ROOT / "app_modules/main_view.py").read_text(encoding="utf-8")

    assert "def render_final_preview_step" not in preview_step
    assert "render_final_preview_step" not in main_view
