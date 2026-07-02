from __future__ import annotations

from app_modules.calculator_component_payload import build_calculator_grid_payload
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult
from calculator.row_model import CalculatorRow


def test_calculator_component_payload_includes_rows_library_and_status() -> None:
    state = CalculatorState(
        itinerary_name="Trip",
        rows=(CalculatorRow(row_id="1", travel_element="hotel", gross_price_per_unit=100, units=2),),
    )
    library_read = LocalLibraryReadResult(
        rows=(
            LocalLibraryRow(
                library_id="lib_1",
                country="NO",
                type="Hotel",
                supplier="Supplier",
                travel_element="Oslo hotel",
                gross_price_per_unit=90,
                units=1,
                supplier_currency="EUR",
                sales_currency="EUR",
            ),
        ),
        source="google_sheets",
        read_only=False,
    )

    payload = build_calculator_grid_payload(state, library_read, show_advanced=True)

    assert payload["itinerary_name"] == "Trip"
    assert payload["show_advanced"] is True
    assert payload["rows"][0]["travel_element"] == "hotel"
    assert payload["rows"][0]["gross_price"] == 200
    assert payload["library_status"] == "Google Sheets connected (1 fetchable lines)."
    assert payload["library_rows"][0]["label"].startswith("NO · Hotel · Supplier")
    assert payload["library_rows"][0]["row_data"]["supplier_commission"] == 0
