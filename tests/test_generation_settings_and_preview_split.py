from __future__ import annotations

from app_modules.generation_settings import build_initial_output_edits, consume_generation_settings, resolve_generation_settings


def test_generation_settings_resolve_brand_language_and_color() -> None:
    settings = resolve_generation_settings(
        {
            "requested_output_brand": "booknordics_customer",
            "requested_presentation_language": "Norwegian",
            "requested_tone_preset": "Professional",
        }
    )

    assert settings.output_brand == "booknordics_customer"
    assert settings.color_preset == "Booknordics B2C"
    assert settings.presentation_language
    assert settings.tone_preset


def test_consume_generation_settings_keeps_only_brand_request_one_shot() -> None:
    state = {
        "requested_output_brand": "booknordics_customer",
        "requested_presentation_language": "English",
        "requested_tone_preset": "Warm",
    }

    settings = consume_generation_settings(state)

    assert settings.output_brand == "booknordics_customer"
    assert "requested_output_brand" not in state
    assert state["requested_presentation_language"] == "English"
    assert state["requested_tone_preset"] == "Warm"


def test_initial_output_edits_owns_generation_brand_metadata() -> None:
    settings = resolve_generation_settings({"requested_output_brand": "agent"})

    output_edits = build_initial_output_edits(
        [{"day": "Day 1", "type": "Activity", "title": "Walk", "city": "Oslo"}],
        {"Day 1": [{"day": "Day 1", "type": "Activity", "title": "Walk", "city": "Oslo"}]},
        settings,
    )

    assert output_edits["output_brand"] == "agent"
    assert output_edits["color_preset"] == "Classic Agent"
    assert output_edits["allow_default_final_images"] is False
