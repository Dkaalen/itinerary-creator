"""Generation settings and initial editable-output state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE, normalize_presentation_language
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET, normalize_tone_preset
from ui.output_edits import make_output_edit_state


@dataclass(frozen=True)
class GenerationSettings:
    """User-facing generation choices resolved before building output edits."""

    output_brand: str
    presentation_language: str
    tone_preset: str
    color_preset: str


def resolve_generation_settings(state: Mapping[str, Any]) -> GenerationSettings:
    """Return normalized generation settings from pending/session state."""

    output_brand = str(state.get("requested_output_brand", "agent") or "agent")
    tone_preset = normalize_tone_preset(
        state.get("requested_tone_preset", state.get("tone_preset", DEFAULT_TONE_PRESET))
    )
    presentation_language = normalize_presentation_language(
        state.get("requested_presentation_language", state.get("presentation_language", DEFAULT_PRESENTATION_LANGUAGE))
    )
    color_preset = "Booknordics B2C" if output_brand == "booknordics_customer" else "Classic Agent"
    return GenerationSettings(
        output_brand=output_brand,
        presentation_language=presentation_language,
        tone_preset=tone_preset,
        color_preset=color_preset,
    )


def consume_generation_settings(state: MutableMapping[str, Any]) -> GenerationSettings:
    """Resolve generation settings and remove one-shot request keys."""

    settings = resolve_generation_settings(state)
    state.pop("requested_output_brand", None)
    return settings


def build_initial_output_edits(
    parsed_rows: list[dict],
    grouped_days: Mapping[Any, list[dict]],
    settings: GenerationSettings,
) -> dict[str, Any]:
    """Build the first editable output model for a generated itinerary."""

    output_edits = make_output_edit_state(parsed_rows, grouped_days, tone_preset=settings.tone_preset)
    output_edits["output_brand"] = settings.output_brand
    output_edits["presentation_language"] = settings.presentation_language
    output_edits["tone_preset"] = settings.tone_preset
    output_edits["color_preset"] = settings.color_preset
    output_edits["allow_default_final_images"] = False
    return output_edits


__all__ = [
    "GenerationSettings",
    "build_initial_output_edits",
    "consume_generation_settings",
    "resolve_generation_settings",
]
