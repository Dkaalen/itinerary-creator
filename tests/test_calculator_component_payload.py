from __future__ import annotations

from app_modules.calculator_component_payload import build_calculator_grid_payload
from calculator.library_fixture import fallback_library_rows
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
    assert isinstance(payload["state_revision"], str)
    assert len(payload["state_revision"]) == 16
    assert payload["rows"][0]["travel_element"] == "hotel"
    assert payload["rows"][0]["gross_price"] == 200
    assert payload["library_status"] == "Local Library connected (1 fetchable lines)."
    assert payload["library_source"] == "google_sheets"
    assert payload["library_read_only"] is False
    assert payload["library_rows"][0]["label"].startswith("NO · Hotel · Supplier")
    assert payload["library_rows"][0]["row_data"]["supplier_commission"] == 0


def test_calculator_component_payload_revision_changes_when_rows_change() -> None:
    library_read = LocalLibraryReadResult(rows=(), source="fixture", read_only=True)
    first = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="hotel"),))
    second = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="museum"),))

    first_payload = build_calculator_grid_payload(first, library_read)
    repeat_payload = build_calculator_grid_payload(first, library_read)
    second_payload = build_calculator_grid_payload(second, library_read)

    assert first_payload["state_revision"] == repeat_payload["state_revision"]
    assert first_payload["state_revision"] != second_payload["state_revision"]



def test_calculator_component_payload_exposes_all_bundled_fallback_rows() -> None:
    library_read = LocalLibraryReadResult(
        rows=fallback_library_rows(),
        source="fixture",
        read_only=True,
        message="Local Library secrets are missing.",
    )

    payload = build_calculator_grid_payload(CalculatorState(), library_read)

    assert len(payload["library_rows"]) == 1145
    assert payload["library_status"] == "Bundled Local Library (1145 autocomplete lines)."
    assert any("Check in to your accommodation" in row["travel_element"] for row in payload["library_rows"])
