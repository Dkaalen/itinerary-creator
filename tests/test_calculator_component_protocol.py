from __future__ import annotations

from app_modules.calculator_component_payload import calculator_state_revision
from app_modules.calculator_component_protocol import (
    acknowledge_calculator_grid_result,
    authorize_calculator_grid_result,
    calculator_component_ack_payload,
)
from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_state_keys import CALCULATOR_PROCESSED_REQUEST_IDS_KEY
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def _state(text: str) -> CalculatorState:
    return CalculatorState(rows=(CalculatorRow(row_id="1", travel_element=text),))


def _result(*, base: CalculatorState, submitted: CalculatorState, request_id: str = "req-1") -> CalculatorGridResult:
    return CalculatorGridResult(
        action="download",
        state=submitted,
        client_state_revision=calculator_state_revision(base),
        request_id=request_id,
    )


def test_protocol_accepts_matching_revision_and_acknowledges_applied_state() -> None:
    session: dict[str, object] = {}
    current = _state("Current")
    submitted = _state("Edited")
    result = _result(base=current, submitted=submitted)

    decision = authorize_calculator_grid_result(session, result, current)

    assert decision.should_process is True
    assert decision.duplicate is False
    acknowledge_calculator_grid_result(
        session,
        result,
        status="accepted",
        server_state=submitted,
    )
    assert calculator_component_ack_payload(session) == {
        "request_id": "req-1",
        "action": "download",
        "status": "accepted",
        "message": "",
        "server_state_revision": calculator_state_revision(submitted),
    }


def test_protocol_rejects_stale_rows_before_backend_state_is_mutated() -> None:
    session: dict[str, object] = {}
    stale_base = _state("Old backend")
    current = _state("New backend")
    stale_submission = _state("Old browser edit")
    result = _result(base=stale_base, submitted=stale_submission)

    decision = authorize_calculator_grid_result(session, result, current)

    assert decision.should_process is False
    assert decision.status == "rejected_stale"
    assert "not applied" in decision.message
    ack = calculator_component_ack_payload(session)
    assert ack["request_id"] == "req-1"
    assert ack["status"] == "rejected_stale"
    assert ack["server_state_revision"] == calculator_state_revision(current)


def test_protocol_treats_replayed_request_as_duplicate_without_new_action() -> None:
    session: dict[str, object] = {}
    current = _state("Current")
    result = _result(base=current, submitted=_state("Edited"))
    assert authorize_calculator_grid_result(session, result, current).should_process is True
    acknowledge_calculator_grid_result(session, result, status="accepted", server_state=result.state)

    duplicate = authorize_calculator_grid_result(session, result, result.state)

    assert duplicate.should_process is False
    assert duplicate.duplicate is True
    assert calculator_component_ack_payload(session)["status"] == "accepted"


def test_protocol_bounds_processed_request_history() -> None:
    session: dict[str, object] = {}
    state = _state("Current")
    for index in range(50):
        result = _result(base=state, submitted=state, request_id=f"req-{index}")
        acknowledge_calculator_grid_result(session, result, status="accepted", server_state=state)

    processed = session[CALCULATOR_PROCESSED_REQUEST_IDS_KEY]
    assert isinstance(processed, list)
    assert len(processed) == 32
    assert processed[0] == "req-49"
    assert processed[-1] == "req-18"


def test_protocol_allows_matching_legacy_action_without_request_id() -> None:
    session: dict[str, object] = {}
    current = _state("Current")
    result = _result(base=current, submitted=_state("Edited"), request_id="")

    decision = authorize_calculator_grid_result(session, result, current)

    assert decision.should_process is True
    acknowledge_calculator_grid_result(session, result, status="accepted", server_state=result.state)
    assert calculator_component_ack_payload(session) == {}
