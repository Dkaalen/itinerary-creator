import importlib
from pathlib import Path


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
    notes = Path("docs/compatibility-facades.md").read_text(encoding="utf-8")

    for facade in REQUIRED_TOP_LEVEL_FACADES:
        assert f"`{facade}.py`" in notes

    assert "Do not delete them just because they look thin" in notes
    assert "Import search shows no app, script, or test imports remain" in notes
