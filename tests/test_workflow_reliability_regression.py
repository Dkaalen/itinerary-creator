from __future__ import annotations

from datetime import datetime, timezone

from app_modules.calculator_currency_controls import CURRENCY_RATES_STATE_KEY
from app_modules.calculator_navigation import CALCULATOR_STATE_KEY
from app_modules.calculator_state_keys import CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY
from app_modules.image_bank_readiness import image_bank_readiness_label, image_bank_readiness_message
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_calculator_state import apply_calculator_snapshot_to_state
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict
from app_modules.workflow_transactions import (
    WorkflowTransactionStatus,
    WorkflowTransactionTarget,
    clear_workflow_transaction,
    retry_workflow_transaction,
    start_workflow_transaction,
    workflow_transaction_state,
)
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def _clock() -> datetime:
    return datetime(2026, 7, 1, 10, 11, 12, tzinfo=timezone.utc)


def test_workflow_transaction_centralizes_pdf_commit_and_auto_create_queue() -> None:
    state: dict[str, object] = {}

    transaction = start_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF, auto_create_pdf=True, now=10.0)

    assert transaction.status == WorkflowTransactionStatus.WAITING_FOR_BROWSER
    assert state["_pdf_auto_create_requested"] is True
    assert state["_pdf_export_job"]["state"] == "saving"
    assert state["_pdf_export_job"]["commit_nonce"] == transaction.commit_nonce

    timed_out = workflow_transaction_state(state, WorkflowTransactionTarget.CREATE_PDF, now=31.0)
    assert timed_out.timed_out is True
    assert int(timed_out.elapsed_seconds) == 21

    retried = retry_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF, auto_create_pdf=True, now=40.0)
    assert retried.commit_nonce != transaction.commit_nonce
    assert state["_pdf_auto_create_requested"] is True

    clear_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF)
    assert state.get("_pdf_after_visual_edit_commit_nonce") is None
    assert state.get("_pdf_export_job") is None
    assert state["_pdf_auto_create_requested"] is False


def test_saved_project_preserves_and_restores_calculator_snapshot() -> None:
    calculator_state = CalculatorState(
        itinerary_name="Calculator Trip",
        rows=(CalculatorRow(row_id="1", day="Day 1", type="Activity", travel_element="Oslo walk"),),
    )
    state = {
        "last_generated_raw_text": "Day 1\tActivity\tOslo walk",
        "parsed_rows": [{"day": "Day 1", "row_id": "row-1", "type": "Activity", "title": "Oslo walk"}],
        "output_edits": {"output_brand": "agent", "rows": {}, "days": {}},
        CALCULATOR_STATE_KEY: calculator_state,
        CURRENCY_RATES_STATE_KEY: {"EUR": 12.5, "USD": 11.0, "NOK": 1.0},
    }

    project = build_saved_project_from_state(state, itinerary_name="Calculator Trip", project_id="calc-1", clock=_clock)
    payload = saved_project_to_dict(project)

    assert payload["calculator_snapshot"]["itinerary_name"] == "Calculator Trip"
    assert payload["calculator_snapshot"]["rows"][0]["travel_element"] == "Oslo walk"
    assert payload["calculator_snapshot"]["currency_rates"]["EUR"] == 12.5

    restored_project = saved_project_from_dict(payload)
    restored_state: dict[str, object] = {}
    apply_calculator_snapshot_to_state(restored_state, restored_project.calculator_snapshot.__dict__)

    restored_calculator = restored_state[CALCULATOR_STATE_KEY]
    assert isinstance(restored_calculator, CalculatorState)
    assert restored_calculator.itinerary_name == "Calculator Trip"
    assert restored_state[CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY] is True
    assert restored_calculator.rows[0].travel_element == "Oslo walk"
    assert restored_state[CURRENCY_RATES_STATE_KEY]["EUR"] == 12.5


def test_image_bank_readiness_copy_prefers_destination_then_fallback() -> None:
    destination_ready = {
        "required_destinations_ready": True,
        "required_destinations": ["Oslo", "Bergen"],
        "covered_destinations": ["Oslo", "Bergen"],
        "destination_image_count": 42,
    }
    fallback_ready = {"default_image_count": 8, "required_destinations": ["Oslo"]}

    assert image_bank_readiness_label(destination_ready) == "Destination images ready"
    assert "2/2 itinerary destinations" in image_bank_readiness_message(destination_ready)
    assert image_bank_readiness_label(fallback_ready) == "Fallback images available"
    assert "Destination images are unavailable" in image_bank_readiness_message(fallback_ready)
