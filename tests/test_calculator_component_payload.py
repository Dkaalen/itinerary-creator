from __future__ import annotations

from app_modules.calculator_component_payload import build_calculator_grid_payload
from calculator.library_workbook import load_local_library_workbook
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult
from calculator.row_model import CalculatorRow


def test_calculator_component_payload_includes_rows_library_and_status() -> None:
    state = CalculatorState(
        itinerary_name="Trip",
        number_of_pax=12,
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
        source="local_excel",
        read_only=True,
    )

    payload = build_calculator_grid_payload(state, library_read, show_advanced=True)

    assert payload["itinerary_name"] == "Trip"
    assert payload["number_of_pax"] == 12
    assert payload["show_advanced"] is True
    assert isinstance(payload["state_revision"], str)
    assert len(payload["state_revision"]) == 16
    assert payload["rows"][0]["travel_element"] == "hotel"
    assert payload["rows"][0]["gross_price"] == 200
    assert payload["library_status"] == "Local Excel Library (1 fetchable lines)."
    assert payload["library_source"] == "local_excel"
    assert payload["library_read_only"] is True
    assert payload["library_rows"][0]["label"].startswith("NO · Hotel · Supplier")
    assert payload["library_rows"][0]["row_data"]["supplier_commission"] == 0


def test_calculator_component_payload_revision_changes_when_rows_change() -> None:
    library_read = LocalLibraryReadResult(rows=(), source="local_excel", read_only=True)
    first = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="hotel"),))
    second = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="museum"),))
    pax_changed = CalculatorState(itinerary_name="Trip", number_of_pax=20, rows=first.rows)

    first_payload = build_calculator_grid_payload(first, library_read)
    repeat_payload = build_calculator_grid_payload(first, library_read)
    second_payload = build_calculator_grid_payload(second, library_read)
    advanced_payload = build_calculator_grid_payload(first, library_read, show_advanced=True)
    changed_rates_payload = build_calculator_grid_payload(first, library_read, currency_rates={"NOK": 1, "EUR": 99})
    pax_payload = build_calculator_grid_payload(pax_changed, library_read)

    assert first_payload["state_revision"] == repeat_payload["state_revision"]
    assert first_payload["state_revision"] != second_payload["state_revision"]
    assert first_payload["state_revision"] == advanced_payload["state_revision"]
    assert first_payload["state_revision"] == changed_rates_payload["state_revision"]
    assert first_payload["state_revision"] != pax_payload["state_revision"]



def test_calculator_component_payload_exposes_bundled_workbook_rows() -> None:
    library = load_local_library_workbook()
    library_read = LocalLibraryReadResult(
        rows=library.rows,
        source="local_excel",
        read_only=True,
        currency_rates=dict(library.currency_rates),
    )

    payload = build_calculator_grid_payload(CalculatorState(), library_read)

    assert len(payload["library_rows"]) == 5946
    assert payload["library_status"] == "Local Excel Library (5946 fetchable lines)."
    assert any("Check in to your accommodation" in row["travel_element"] for row in payload["library_rows"])
