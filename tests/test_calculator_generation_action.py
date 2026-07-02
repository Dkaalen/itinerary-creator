from __future__ import annotations

from app_modules.calculator_navigation import CALCULATOR_PAGE
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
    assert calls["raw_text"] == "Day 1\tActivity\t\t\t\t\t\t\tTromsø: Northern lights chase"


def test_generate_itinerary_from_calculator_blocks_empty_calculator_rows() -> None:
    session_state = {"active_app_page": CALCULATOR_PAGE}
    calculator_state = CalculatorState(rows=(CalculatorRow(row_id="1"),))

    result = generate_itinerary_from_calculator(session_state, calculator_state)

    assert result.ok is False
    assert result.stage == "input"
    assert "Add at least one calculator row" in result.message
    assert session_state["active_app_page"] == CALCULATOR_PAGE
