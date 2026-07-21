import importlib
from pathlib import Path
from tests.support.static_contracts import read_contract_text


REQUIRED_TOP_LEVEL_FACADES = {
    "generator": "itinerary_generation",
    "itinerary_parser": "parser_modules",
    "normalizer": "normalizer_modules",
    "text_polish": "text_polish_modules",
    "image_matcher": "images",
    "pdf_exporter": "pdf_exporter_modules",
}

REQUIRED_UI_FACADES = {
    "ui.accommodation_display_helpers": "itinerary_generation.accommodation_display_helpers",
    "ui.activity_description_helpers": "itinerary_generation.activity_description_helpers",
    "ui.activity_inclusions": "itinerary_generation.activity_inclusions",
    "ui.activity_logistics": "itinerary_generation.activity_logistics",
    "ui.render_text_helpers": "itinerary_generation.render_text_helpers",
    "ui.time_display": "itinerary_generation.time_display",
    "ui.transport_display_helpers": "itinerary_generation.transport_display_helpers",
}

REQUIRED_GENERATION_FACADES = {
    "itinerary_generation.day_text": "itinerary_generation.day_intro_engine",
    "itinerary_generation.day_intro_planner": "itinerary_generation.day_intro_engine",
    "itinerary_generation.source_identity": "shared.source_rows",
}


def test_required_top_level_facades_remain_importable_and_documented():
    for facade, owner_package in REQUIRED_TOP_LEVEL_FACADES.items():
        module = importlib.import_module(facade)
        assert module.__doc__
        assert "Compatibility" in module.__doc__ or "compatibility" in module.__doc__
        assert importlib.import_module(owner_package)


def test_required_ui_facades_remain_importable_and_documented():
    for facade, owner_module in REQUIRED_UI_FACADES.items():
        module = importlib.import_module(facade)
        assert module.__doc__
        assert "Compatibility" in module.__doc__ or "compatibility" in module.__doc__
        assert importlib.import_module(owner_module)


def test_required_generation_facades_remain_importable_and_documented():
    for facade, owner_module in REQUIRED_GENERATION_FACADES.items():
        module = importlib.import_module(facade)
        assert module.__doc__
        assert "Compatibility" in module.__doc__ or "compatibility" in module.__doc__
        assert importlib.import_module(owner_module)


def test_facade_audit_notes_are_kept_with_architecture_docs():
    notes = read_contract_text("docs/compatibility-facades.md")

    for facade in REQUIRED_TOP_LEVEL_FACADES:
        assert f"`{facade}.py`" in notes

    assert "Do not delete them just because they look thin" in notes
    assert "Import search shows no app, script, or test imports remain" in notes


def test_retired_ui_render_facades_remain_absent_and_owners_stay_available():
    retired_modules = {"ui.day_overview_blocks", "ui.transport_row_blocks"}
    assert all(importlib.util.find_spec(module_name) is None for module_name in retired_modules)

    root = Path(__file__).resolve().parents[1]
    production_roots = (
        root / "app.py",
        root / "app_modules",
        root / "calculator",
        root / "images",
        root / "itinerary_domain",
        root / "itinerary_generation",
        root / "normalizer_modules",
        root / "parser_modules",
        root / "pdf_exporter_modules",
        root / "project_storage",
        root / "shared",
        root / "text_polish_modules",
        root / "ui",
        root / "visual_editor_component",
    )
    production_files = []
    for source in production_roots:
        if source.is_file():
            production_files.append(source)
        elif source.exists():
            production_files.extend(source.rglob("*.py"))
    offenders = []
    for source in production_files:
        text = source.read_text(encoding="utf-8", errors="ignore")
        for module_name in retired_modules:
            if module_name in text or module_name.replace(".", "/") + ".py" in text:
                offenders.append(str(source.relative_to(root)))
    assert offenders == []

    from itinerary_generation.day_overview_blocks import build_day_overview_render_block
    from itinerary_generation.transport_render_blocks import build_transport_render_block
    from ui.day_blocks import build_day_overview_block

    assert callable(build_day_overview_render_block)
    assert callable(build_day_overview_block)
    assert callable(build_transport_render_block)
