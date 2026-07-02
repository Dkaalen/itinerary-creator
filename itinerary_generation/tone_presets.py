"""Controlled generation tone presets for itinerary prose."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_TONE_PRESET = "premium_concise"


@dataclass(frozen=True, slots=True)
class TonePreset:
    id: str
    label: str
    detail_level: str
    intro_prefix: str = ""
    title_suffix: str = ""


TONE_PRESETS: dict[str, TonePreset] = {
    "premium_concise": TonePreset("premium_concise", "Premium concise", "Standard client itinerary"),
    "warm_descriptive": TonePreset("warm_descriptive", "Warm descriptive", "Rich descriptive", "Enjoy a well-paced day with "),
    "luxury_editorial": TonePreset("luxury_editorial", "Luxury editorial", "Rich descriptive", "A polished day unfolds with "),
    "minimal_agent": TonePreset("minimal_agent", "Minimal agent version", "Standard client itinerary"),
    "family_friendly": TonePreset("family_friendly", "Family friendly", "Rich descriptive", "A comfortable family-friendly day includes "),
    "adventure_focused": TonePreset("adventure_focused", "Adventure focused", "Rich descriptive", "Set out for an active day featuring "),
}


def normalize_tone_preset(value: Any) -> str:
    preset = str(value or DEFAULT_TONE_PRESET).strip().lower().replace(" ", "_").replace("-", "_")
    return preset if preset in TONE_PRESETS else DEFAULT_TONE_PRESET


def tone_preset(value: Any = DEFAULT_TONE_PRESET) -> TonePreset:
    return TONE_PRESETS[normalize_tone_preset(value)]


def apply_tone_to_title(title: str, preset_id: Any) -> str:
    """Return a safely polished title without changing structure."""

    preset = tone_preset(preset_id)
    text = str(title or "").strip()
    if not text:
        return text
    if preset.id == "minimal_agent":
        return text.split(" — ", 1)[0].strip()
    return text


def apply_tone_to_intro(intro: str, preset_id: Any) -> str:
    """Return tone-adjusted intro text while preserving generated facts."""

    preset = tone_preset(preset_id)
    text = str(intro or "").strip()
    if not text or not preset.intro_prefix:
        return text
    lowered = text[:1].lower() + text[1:]
    if lowered.startswith(preset.intro_prefix.lower()):
        return text
    return f"{preset.intro_prefix}{lowered}"


__all__ = [
    "DEFAULT_TONE_PRESET",
    "TONE_PRESETS",
    "TonePreset",
    "apply_tone_to_intro",
    "apply_tone_to_title",
    "normalize_tone_preset",
    "tone_preset",
]
