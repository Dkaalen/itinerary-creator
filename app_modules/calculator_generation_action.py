"""Generate itinerary output from calculator state."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.calculator_navigation import close_calculator_page
from app_modules.calculator_state_keys import (
    CALCULATOR_RETURN_AVAILABLE_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from app_modules.generation_action import generate_itinerary
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import normalise_stage, set_workflow_stage
from calculator.calculator_state import CalculatorState
from calculator.to_itinerary_input import calculator_state_to_raw_input
from calculator.validation import CalculatorValidationScope, validate_calculator_state
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET


def generate_itinerary_from_calculator(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    output_brand: str = "agent",
) -> WorkflowActionResult:
    """Convert calculator rows and run the existing itinerary generator."""

    previous_stage = normalise_stage(state.get("app_stage", "input"))
    validation_issues = validate_calculator_state(
        calculator_state,
        state.get(CURRENCY_RATES_STATE_KEY),
        scope=CalculatorValidationScope.GENERATION,
    )
    if validation_issues:
        return WorkflowActionResult(
            ok=False,
            stage=previous_stage,
            message=validation_issues[0].message,
            payload={"calculator_validation_issues": validation_issues},
        )

    raw_text = calculator_state_to_raw_input(calculator_state)
    _seed_generation_request(state, calculator_state, output_brand)
    result = generate_itinerary(state, raw_text)
    if result.ok:
        state[CALCULATOR_RETURN_AVAILABLE_KEY] = True
        close_calculator_page(state)
        return result

    restored_stage = set_workflow_stage(state, previous_stage)
    return WorkflowActionResult(
        ok=False,
        stage=restored_stage,
        message=result.message,
        payload=result.payload,
    )


def _seed_generation_request(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    output_brand: str,
) -> None:
    itinerary_name = " ".join(str(calculator_state.itinerary_name or "").split())
    state["itinerary_name"] = itinerary_name
    state["itinerary_name_input"] = itinerary_name
    state["requested_output_brand"] = output_brand
    state["requested_presentation_language"] = state.get("presentation_language", DEFAULT_PRESENTATION_LANGUAGE)
    state["requested_tone_preset"] = state.get("tone_preset", DEFAULT_TONE_PRESET)
