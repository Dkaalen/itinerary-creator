"""Generate itinerary output from calculator state."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.calculator_state_keys import (
    CURRENCY_RATES_STATE_KEY,
)
from app_modules.calculator_generation_rows import (
    calculator_rows_have_library_provenance,
    parse_and_normalize_calculator_rows,
)
from app_modules.generation_action import generate_itinerary
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_navigation import normalize_workflow_stage
from app_modules.session_state_keys import (
    APP_STAGE_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    PRESENTATION_LANGUAGE_KEY,
    REQUESTED_OUTPUT_BRAND_KEY,
    REQUESTED_PRESENTATION_LANGUAGE_KEY,
    REQUESTED_TONE_PRESET_KEY,
    TONE_PRESET_KEY,
)
from app_modules.calculator_lifecycle import complete_calculator_generation, fail_calculator_generation
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

    previous_stage = normalize_workflow_stage(state.get(APP_STAGE_KEY, "input"))
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
    prepared_rows = (
        parse_and_normalize_calculator_rows(calculator_state.rows)
        if calculator_rows_have_library_provenance(calculator_state.rows)
        else None
    )
    _seed_generation_request(state, calculator_state, output_brand)
    result = (
        generate_itinerary(state, raw_text, prepared_parsed_rows=prepared_rows)
        if prepared_rows is not None
        else generate_itinerary(state, raw_text)
    )
    if result.ok:
        complete_calculator_generation(state)
        return result

    restored_stage = fail_calculator_generation(state, previous_stage)
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
    state[ITINERARY_NAME_KEY] = itinerary_name
    state[ITINERARY_NAME_INPUT_KEY] = itinerary_name
    state[REQUESTED_OUTPUT_BRAND_KEY] = output_brand
    state[REQUESTED_PRESENTATION_LANGUAGE_KEY] = state.get(PRESENTATION_LANGUAGE_KEY, DEFAULT_PRESENTATION_LANGUAGE)
    state[REQUESTED_TONE_PRESET_KEY] = state.get(TONE_PRESET_KEY, DEFAULT_TONE_PRESET)
