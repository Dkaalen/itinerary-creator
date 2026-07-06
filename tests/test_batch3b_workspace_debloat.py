from pathlib import Path
from types import SimpleNamespace

from app_modules import input_step
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET


def test_input_page_removes_fixed_language_and_tone_controls() -> None:
    source = Path("app_modules/input_step.py").read_text(encoding="utf-8")

    assert "Presentation language" not in source
    assert "Tone preset" not in source
    assert "render_presentation_language_selector" not in source
    assert "render_tone_preset_selector" not in source
    assert "DEFAULT_PRESENTATION_LANGUAGE" in source
    assert "DEFAULT_TONE_PRESET" in source


def test_language_and_tone_selectors_are_removed_from_normal_ui() -> None:
    assert not Path("app_modules/presentation_language_ui.py").exists()
    assert not Path("app_modules/tone_preset_ui.py").exists()


def test_generate_itinerary_forces_fixed_language_and_tone(monkeypatch) -> None:
    state = {
        "presentation_language": "fr",
        "tone_preset": "luxury_editorial",
        "itinerary_name_input": "Norway Winter",
    }

    fake_st = SimpleNamespace(session_state=state)
    monkeypatch.setattr(input_step, "st", fake_st)
    monkeypatch.setattr(input_step, "sync_itinerary_name_from_input", lambda _state: None)
    monkeypatch.setattr(input_step, "generate_itinerary", lambda _state, _raw_text: SimpleNamespace(ok=True, payload={}))

    assert input_step._generate_itinerary("Day 1\tHotel") is True
    assert state["presentation_language"] == DEFAULT_PRESENTATION_LANGUAGE
    assert state["tone_preset"] == DEFAULT_TONE_PRESET
    assert state["requested_presentation_language"] == DEFAULT_PRESENTATION_LANGUAGE
    assert state["requested_tone_preset"] == DEFAULT_TONE_PRESET
