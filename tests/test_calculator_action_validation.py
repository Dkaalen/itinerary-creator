from __future__ import annotations

from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_page import (
    _component_action_validation_issues,
    _component_result_updates_session_state,
)
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_serialization import saved_project_to_dict
from app_modules.saved_project_validation import validate_saved_project_payload
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.validation import CalculatorValidationScope, validate_calculator_state


def _invalid_financial_state() -> CalculatorState:
    return CalculatorState(
        itinerary_name="Draft",
        number_of_pax="2.5",
        rows=(
            CalculatorRow(
                row_id="7",
                day="Day 1",
                type="Hotel",
                travel_element="Oslo hotel",
                gross_price_per_unit="=10/0",
                supplier_currency="XYZ",
                sales_currency="NOK",
            ),
        ),
    )


def test_draft_safe_navigation_never_blocks_incomplete_or_invalid_rows() -> None:
    assert validate_calculator_state(
        _invalid_financial_state(),
        scope=CalculatorValidationScope.DRAFT_SAFE,
    ) == ()


def test_export_validates_financial_cells_but_ignores_passenger_count() -> None:
    state = CalculatorState(
        number_of_pax="2.5",
        rows=(
            CalculatorRow(
                row_id="1",
                gross_price_per_unit=100,
                units=1,
                supplier_currency="NOK",
                sales_currency="NOK",
            ),
        ),
    )

    assert validate_calculator_state(state, scope=CalculatorValidationScope.EXPORT) == ()

    broken = CalculatorState(
        number_of_pax="2.5",
        rows=(CalculatorRow(row_id="1", gross_price_per_unit="=10/0"),),
    )
    issues = validate_calculator_state(broken, scope=CalculatorValidationScope.EXPORT)
    assert issues[0].row_id == "1"
    assert issues[0].field == "gross_price_per_unit"


def test_generation_validates_only_itinerary_fields_with_row_diagnostics() -> None:
    finance_error_is_irrelevant = _invalid_financial_state()
    assert validate_calculator_state(
        finance_error_is_irrelevant,
        scope=CalculatorValidationScope.GENERATION,
    ) == ()

    incomplete = CalculatorState(
        rows=(
            CalculatorRow(row_id="11", day="Day 1", travel_element="Oslo hotel"),
            CalculatorRow(row_id="12", day="Day 2", type="Activity"),
        )
    )
    issues = validate_calculator_state(incomplete, scope=CalculatorValidationScope.GENERATION)
    assert [(issue.row_id, issue.field) for issue in issues] == [
        ("11", "type"),
        ("12", "travel_element"),
    ]


def test_persistence_accepts_incomplete_rows_but_rejects_corrupt_formulas() -> None:
    incomplete = CalculatorState(
        rows=(CalculatorRow(row_id="1", day="Day 1", type="Hotel", travel_element=""),)
    )
    assert validate_calculator_state(
        incomplete,
        scope=CalculatorValidationScope.PERSISTENCE,
    ) == ()

    broken = CalculatorState(rows=(CalculatorRow(row_id="1", gross_price_per_unit="=10/0"),))
    issues = validate_calculator_state(broken, scope=CalculatorValidationScope.PERSISTENCE)
    assert issues[0].row_id == "1"
    assert issues[0].field == "gross_price_per_unit"


def test_saved_project_payload_accepts_an_incomplete_calculator_draft() -> None:
    state = {
        "itinerary_name": "Draft project",
        "calculator_state": CalculatorState(
            itinerary_name="Draft project",
            rows=(CalculatorRow(row_id="1", day="Day 1", type="Hotel"),),
        ),
    }
    payload = saved_project_to_dict(build_saved_project_from_state(state, itinerary_name="Draft project"))

    validate_saved_project_payload(payload)


def test_invalid_browser_drafts_remain_browser_authority_for_navigation_and_generation() -> None:
    state = _invalid_financial_state()
    for action in ("close", "open_library", "generate_agent", "generate_customer"):
        result = CalculatorGridResult(
            action=action,
            state=state,
            client_has_validation_errors=True,
        )
        assert _component_result_updates_session_state(result) is False

    assert _component_result_updates_session_state(
        CalculatorGridResult(action="download", state=state, client_has_validation_errors=True)
    ) is True
    assert _component_result_updates_session_state(
        CalculatorGridResult(action="open_excel", state=state)
    ) is False


def test_backend_revalidates_action_scope_without_trusting_client_flags() -> None:
    invalid = _invalid_financial_state()
    download = CalculatorGridResult(
        action="download",
        state=invalid,
        client_has_validation_errors=False,
    )
    navigation = CalculatorGridResult(
        action="close",
        state=invalid,
        client_has_validation_errors=False,
    )

    download_issues = _component_action_validation_issues(download)
    assert download_issues
    assert download_issues[0].row_id == "7"
    assert _component_action_validation_issues(navigation) == ()
    assert _component_result_updates_session_state(navigation) is False


def test_persistence_accepts_numeric_whole_pax_but_rejects_fractional_pax() -> None:
    whole = CalculatorState(number_of_pax="2.0")
    fractional = CalculatorState(number_of_pax=2.5)

    assert validate_calculator_state(whole, scope=CalculatorValidationScope.PERSISTENCE) == ()
    issues = validate_calculator_state(fractional, scope=CalculatorValidationScope.PERSISTENCE)
    assert issues[0].field == "number_of_pax"
