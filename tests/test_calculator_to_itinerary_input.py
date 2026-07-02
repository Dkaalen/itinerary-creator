from __future__ import annotations

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.to_itinerary_input import (
    calculator_rows_to_raw_input,
    calculator_state_to_raw_input,
    generatable_row_count,
    row_is_generatable,
)
from itinerary_parser import parse_itinerary


def test_calculator_rows_convert_to_existing_tab_separated_input_shape() -> None:
    row = CalculatorRow(
        row_id="1",
        day="1",
        type="Activity",
        from_date="01/10/2026",
        from_time="10:30",
        to_time="12:45",
        supplier="Local Guide",
        travel_element="Helsinki: A Finntastic Walking Tour",
        comments="Meeting point: Senate Square",
        url="https://example.com/tour",
    )

    raw_input = calculator_rows_to_raw_input((row,))

    assert raw_input == (
        "Day 1\tActivity\t\t01/10/2026\t\t10:30\t12:45\tLocal Guide\t"
        "Helsinki: A Finntastic Walking Tour - Time: 10:30 - 12:45 - "
        "Meeting point: Senate Square - URL: https://example.com/tour"
    )


def test_calculator_state_to_raw_input_can_be_parsed_by_existing_parser() -> None:
    state = CalculatorState(
        itinerary_name="Helsinki",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Transfer",
                from_date="01/10/2026",
                travel_element="Helsinki: Private Airport to Hotel",
            ),
        ),
    )

    parsed_rows = parse_itinerary(calculator_state_to_raw_input(state))

    assert len(parsed_rows) == 1
    assert parsed_rows[0]["day"] == "Day 1"
    assert parsed_rows[0]["type"] == "Transfer"
    assert parsed_rows[0]["city"] == "Helsinki"
    assert "Airport" in parsed_rows[0]["title"]


def test_generatable_rows_require_type_and_travel_element() -> None:
    valid = CalculatorRow(type="Hotel", travel_element="Scandic Hotel")
    missing_type = CalculatorRow(travel_element="Scandic Hotel")
    missing_text = CalculatorRow(type="Hotel")

    assert row_is_generatable(valid) is True
    assert row_is_generatable(missing_type) is False
    assert row_is_generatable(missing_text) is False
    assert generatable_row_count((valid, missing_type, missing_text)) == 1
