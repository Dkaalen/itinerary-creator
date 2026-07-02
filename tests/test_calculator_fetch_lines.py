from __future__ import annotations

from calculator.calculator_state import CalculatorState, add_row
from calculator.fetch_lines import (
    autofill_exact_travel_element_matches,
    calculator_row_from_library_line,
    fetch_library_line_into_first_available_row,
    fetch_library_line_into_row,
)
from calculator.library_model import LocalLibraryRow
from calculator.row_model import CalculatorRow


def test_calculator_row_from_library_line_copies_fetchable_fields_without_metadata() -> None:
    library_row = LocalLibraryRow(
        library_id="lib_1",
        day="Day 2",
        type="Activity",
        supplier="Supplier",
        travel_element="Northern lights chase",
        gross_price_per_unit=1200,
        units=2,
        supplier_commission=0.1,
        supplier_currency="NOK",
        sales_price_per_unit=1500,
        sales_currency="NOK",
        comments="Warm clothes included",
    )

    row = calculator_row_from_library_line(library_row, row_id="7")

    assert row.row_id == "7"
    assert row.type == "Activity"
    assert row.supplier == "Supplier"
    assert row.travel_element == "Northern lights chase"
    assert row.gross_price_per_unit == 1200
    assert row.sales_price_per_unit == 1500
    assert row.comments == "Warm clothes included"


def test_fetch_library_line_replaces_selected_calculator_row_and_preserves_other_rows() -> None:
    state = CalculatorState(itinerary_name="Trip")
    state = add_row(state, CalculatorRow(travel_element="Old selected"))
    state = add_row(state, CalculatorRow(travel_element="Keep"))
    library_row = LocalLibraryRow(type="Hotel", travel_element="Fetched hotel", gross_price_per_unit=200)

    updated = fetch_library_line_into_row(state, library_row, target_row_id="1")

    assert updated.itinerary_name == "Trip"
    assert [row.row_id for row in updated.rows] == ["1", "2"]
    assert updated.rows[0].type == "Hotel"
    assert updated.rows[0].travel_element == "Fetched hotel"
    assert updated.rows[0].gross_price_per_unit == 200
    assert updated.rows[1].travel_element == "Keep"


def test_fetch_library_line_appends_when_no_target_row_is_selected() -> None:
    state = add_row(CalculatorState(), CalculatorRow(travel_element="Existing"))
    library_row = LocalLibraryRow(type="Transfer", travel_element="Fetched transfer")

    updated = fetch_library_line_into_row(state, library_row, target_row_id=None)

    assert [row.row_id for row in updated.rows] == ["1", "2"]
    assert updated.rows[1].type == "Transfer"


def test_fetch_library_line_uses_first_empty_row_before_appending() -> None:
    state = add_row(CalculatorState(), CalculatorRow(type="Hotel", travel_element="Existing"))
    state = add_row(state, CalculatorRow(day="Day 2"))
    library_row = LocalLibraryRow(type="Transfer", travel_element="Fetched transfer")

    updated = fetch_library_line_into_first_available_row(state, library_row)

    assert [row.row_id for row in updated.rows] == ["1", "2"]
    assert updated.rows[1].day == "Day 2"
    assert updated.rows[1].type == "Transfer"
    assert updated.rows[1].travel_element == "Fetched transfer"


def test_autofill_exact_travel_element_match_preserves_day_context() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(row_id="1", day="Day 3", travel_element="Helsinki: A Finntastic Walking Tour"),
        )
    )
    library_row = LocalLibraryRow(
        library_id="fixture_helsinki_walk",
        type="Activity",
        supplier="Finntastic Tours",
        travel_element="Helsinki: A Finntastic Walking Tour",
        gross_price_per_unit=25,
        units=1,
        supplier_currency="EUR",
        sales_currency="EUR",
    )

    updated = autofill_exact_travel_element_matches(state, (library_row,))

    assert updated.rows[0].row_id == "1"
    assert updated.rows[0].day == "Day 3"
    assert updated.rows[0].type == "Activity"
    assert updated.rows[0].supplier == "Finntastic Tours"
    assert updated.rows[0].gross_price_per_unit == 25


def test_autofill_does_not_overwrite_manually_priced_rows() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(
                row_id="1",
                travel_element="Helsinki: A Finntastic Walking Tour",
                gross_price_per_unit=99,
            ),
        )
    )
    library_row = LocalLibraryRow(
        travel_element="Helsinki: A Finntastic Walking Tour",
        gross_price_per_unit=25,
    )

    updated = autofill_exact_travel_element_matches(state, (library_row,))

    assert updated == state
