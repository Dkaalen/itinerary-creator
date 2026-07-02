from __future__ import annotations

from calculator.grid_autocomplete import find_travel_element_suggestion_groups
from calculator.library_model import LocalLibraryRow
from calculator.row_model import CalculatorRow


def test_grid_autocomplete_suggests_rows_from_typed_travel_element() -> None:
    rows = (
        CalculatorRow(row_id="1", travel_element="hotel"),
        CalculatorRow(row_id="2", travel_element=""),
    )
    library_rows = (
        LocalLibraryRow(library_id="hotel_oslo", type="Hotel", country="NO", travel_element="Oslo hotel check in"),
        LocalLibraryRow(library_id="walk", type="Activity", country="FI", travel_element="Walking tour"),
    )

    groups = find_travel_element_suggestion_groups(rows, library_rows)

    assert len(groups) == 1
    assert groups[0].row_id == "1"
    assert groups[0].query == "hotel"
    assert groups[0].results[0].row.library_id == "hotel_oslo"


def test_grid_autocomplete_skips_priced_or_fetched_rows() -> None:
    rows = (
        CalculatorRow(row_id="1", travel_element="hotel", gross_price_per_unit=100),
        CalculatorRow(row_id="2", travel_element="walking tour", supplier="Manual supplier"),
    )
    library_rows = (
        LocalLibraryRow(library_id="hotel_oslo", type="Hotel", travel_element="Oslo hotel check in"),
        LocalLibraryRow(library_id="walk", type="Activity", travel_element="Walking tour"),
    )

    assert find_travel_element_suggestion_groups(rows, library_rows) == ()


def test_grid_autocomplete_limits_to_first_active_row_by_default() -> None:
    rows = (
        CalculatorRow(row_id="1", travel_element="hotel"),
        CalculatorRow(row_id="2", travel_element="transfer"),
    )
    library_rows = (
        LocalLibraryRow(library_id="hotel_oslo", type="Hotel", travel_element="Oslo hotel check in"),
        LocalLibraryRow(library_id="transfer", type="Transfer", travel_element="Airport transfer"),
    )

    groups = find_travel_element_suggestion_groups(rows, library_rows)

    assert [group.row_id for group in groups] == ["1"]
