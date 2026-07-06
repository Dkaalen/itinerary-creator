"""Supplier-text generation action for the input page."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_name_state import sync_itinerary_name_from_input
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from app_modules.validation_gate import block_generation, render_blocking_issues
from app_modules.workflow_actions import generate_itinerary
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET


def generate_supplier_itinerary(state: MutableMapping[str, Any], raw_text: str, output_brand: str = "agent") -> bool:
    """Generate an itinerary from supplier text and render blocking issues."""

    sync_itinerary_name_from_input(state)
    state["requested_output_brand"] = output_brand
    state["presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    state["tone_preset"] = DEFAULT_TONE_PRESET
    state["requested_presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    state["requested_tone_preset"] = DEFAULT_TONE_PRESET
    result = generate_itinerary(state, raw_text)
    if not result.ok:
        validation_report = (result.payload or {}).get("validation_report")
        if validation_report is not None:
            block_generation(validation_report)
            render_blocking_issues(validation_report)
        return False
    return True


def reset_input_generation_defaults(state: MutableMapping[str, Any]) -> None:
    """Reset request defaults owned by the input page before rendering controls."""

    state["presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    state["tone_preset"] = DEFAULT_TONE_PRESET
