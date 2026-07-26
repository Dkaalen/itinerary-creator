from __future__ import annotations

from app_modules.calculator_navigation import CALCULATOR_PAGE
from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY
from app_modules.calculator_generation_action import generate_itinerary_from_calculator
from app_modules.workflow_result import WorkflowActionResult
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def test_generate_itinerary_from_calculator_reuses_existing_generation_pipeline(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_generate_itinerary(state, raw_text):
        calls["state"] = state
        calls["raw_text"] = raw_text
        state["parsed_rows"] = [{"day": "Day 1"}]
        return WorkflowActionResult(ok=True, stage="edit", message="ok")

    monkeypatch.setattr(
        "app_modules.calculator_generation_action.generate_itinerary",
        fake_generate_itinerary,
    )
    session_state = {
        "active_app_page": CALCULATOR_PAGE,
        "presentation_language": "English",
        "tone_preset": "Premium concise",
    }
    calculator_state = CalculatorState(
        itinerary_name="Tromsø Northern Lights",
        rows=(CalculatorRow(row_id="1", day="Day 1", type="Activity", travel_element="Tromsø: Northern lights chase"),),
    )

    result = generate_itinerary_from_calculator(session_state, calculator_state, output_brand="booknordics_customer")

    assert result.ok is True
    assert session_state["active_app_page"] == "workflow"
    assert session_state["itinerary_name"] == "Tromsø Northern Lights"
    assert session_state["requested_output_brand"] == "booknordics_customer"
    assert session_state[CALCULATOR_RETURN_AVAILABLE_KEY] is True
    assert calls["raw_text"] == "Day 1\tActivity\t\t\t\t\t\t\tTromsø: Northern lights chase"


def test_generate_itinerary_from_calculator_blocks_empty_calculator_rows() -> None:
    session_state = {"active_app_page": CALCULATOR_PAGE}
    calculator_state = CalculatorState(rows=(CalculatorRow(row_id="1"),))

    result = generate_itinerary_from_calculator(session_state, calculator_state)

    assert result.ok is False
    assert result.stage == "input"
    assert "Add at least one calculator row" in result.message
    assert session_state["active_app_page"] == CALCULATOR_PAGE
    assert CALCULATOR_RETURN_AVAILABLE_KEY not in session_state


def test_generation_validation_keeps_existing_workflow_stage() -> None:
    session_state = {"active_app_page": CALCULATOR_PAGE, "app_stage": "edit"}
    calculator_state = CalculatorState(
        rows=(CalculatorRow(row_id="4", day="Day 1", type="Hotel"),)
    )

    result = generate_itinerary_from_calculator(session_state, calculator_state)

    assert result.ok is False
    assert result.stage == "edit"
    assert session_state["app_stage"] == "edit"
    assert "Row 4" in result.message
    assert "Travel element" in result.message


def test_downstream_generation_failure_restores_existing_workflow_stage(monkeypatch) -> None:
    def fail_generation(state, _raw_text):
        state["app_stage"] = "input"
        return WorkflowActionResult(ok=False, stage="input", message="blocked")

    monkeypatch.setattr("app_modules.calculator_generation_action.generate_itinerary", fail_generation)
    session_state = {"active_app_page": CALCULATOR_PAGE, "app_stage": "pictures"}
    calculator_state = CalculatorState(
        rows=(CalculatorRow(row_id="1", type="Hotel", travel_element="Oslo hotel"),)
    )

    result = generate_itinerary_from_calculator(session_state, calculator_state)

    assert result.ok is False
    assert result.stage == "pictures"
    assert session_state["app_stage"] == "pictures"
    assert session_state["active_app_page"] == CALCULATOR_PAGE


def test_generate_itinerary_from_sourced_rows_passes_prepared_provenance(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_generate_itinerary(state, raw_text, *, prepared_parsed_rows=None):
        calls["raw_text"] = raw_text
        calls["prepared_rows"] = prepared_parsed_rows
        state["parsed_rows"] = prepared_parsed_rows or []
        return WorkflowActionResult(ok=True, stage="edit", message="ok")

    monkeypatch.setattr(
        "app_modules.calculator_generation_action.generate_itinerary",
        fake_generate_itinerary,
    )
    calculator_state = CalculatorState(
        itinerary_name="Workbook lineage",
        rows=(
            CalculatorRow(
                row_id="4",
                day="Day 1",
                type="Activity",
                travel_element="Rovaniemi: Northern lights hunt",
                url="https://supplier.invalid/activity",
                library_id="activities_row_19",
                source_workbook="Calculation-template-Inputs-fixed-outline-restored.xlsx",
                source_sheet="Activities",
                source_row=19,
            ),
        ),
    )

    result = generate_itinerary_from_calculator(
        {"active_app_page": CALCULATOR_PAGE}, calculator_state
    )

    assert result.ok is True
    prepared = calls["prepared_rows"]
    assert isinstance(prepared, list)
    assert prepared[0]["library_id"] == "activities_row_19"
    assert prepared[0]["source_sheet"] == "Activities"
    assert prepared[0]["source_row"] == 19
    assert prepared[0]["source_url"] == "https://supplier.invalid/activity"
    assert "supplier.invalid" not in str(calls["raw_text"])
