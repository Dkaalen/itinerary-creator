from __future__ import annotations

import json

from app_modules.calculator_component_payload import (
    build_calculator_grid_payload,
    clear_calculator_library_payload_cache,
)
from calculator.library_workbook import load_local_library_workbook
from calculator.calculator_state import CalculatorState
from calculator.financial_rules import FINANCIAL_RULES_VERSION, financial_rules_payload
from calculator.library_model import LocalLibraryRow
from calculator.library_ranking import LOCAL_LIBRARY_RANKING_SPEC, LOCAL_LIBRARY_RANKING_VERSION
from calculator.library_store import LocalLibraryReadResult
from calculator.row_model import CalculatorRow


def _expand_compact_row(payload: dict, index: int = 0) -> dict:
    compact = payload["library_rows"][index]
    row_data = {
        payload["library_row_fields"][int(index)]: value
        for index, value in compact["v"].items()
    }
    return {
        "library_id": compact["i"],
        "source_workbook": compact.get("b", ""),
        "source_sheet": compact["w"],
        "source_row": compact["x"],
        "country": compact["c"],
        "category": compact["g"],
        "row_data": row_data,
    }


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
                supplier_commission=0.15,
                supplier_currency="EUR",
                sales_currency="EUR",
            ),
        ),
        source="local_excel",
        read_only=True,
        fingerprint="fixture-1",
    )

    payload = build_calculator_grid_payload(state, library_read, show_advanced=True)
    library_row = _expand_compact_row(payload)

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
    assert payload["library_payload_version"] == "compact-v3"
    assert payload["library_fingerprint"] == f"compact-v3:{LOCAL_LIBRARY_RANKING_VERSION}:fixture-1"
    assert payload["library_ranking_spec"] == LOCAL_LIBRARY_RANKING_SPEC
    assert payload["financial_rules"] == financial_rules_payload()
    assert payload["financial_rules"]["version"] == FINANCIAL_RULES_VERSION
    assert library_row["country"] == "NO"
    assert library_row["row_data"]["type"] == "Hotel"
    assert library_row["row_data"]["supplier"] == "Supplier"
    assert library_row["row_data"]["supplier_commission"] == 15
    assert library_row["row_data"]["gross_price_per_unit"] == 90


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


def test_calculator_component_payload_reuses_prepared_library_rows() -> None:
    clear_calculator_library_payload_cache()
    library_read = LocalLibraryReadResult(
        rows=(LocalLibraryRow(library_id="one", travel_element="Hotel"),),
        source="local_excel",
        read_only=True,
        fingerprint="same-workbook",
    )

    first = build_calculator_grid_payload(CalculatorState(), library_read)
    second = build_calculator_grid_payload(CalculatorState(), library_read)

    assert first["library_rows"] is second["library_rows"]


def test_calculator_component_payload_exposes_bundled_workbook_rows_compactly() -> None:
    library = load_local_library_workbook()
    library_read = LocalLibraryReadResult(
        rows=library.rows,
        source="local_excel",
        read_only=True,
        currency_rates=dict(library.currency_rates),
        fingerprint=library.fingerprint,
    )

    payload = build_calculator_grid_payload(CalculatorState(), library_read)
    fields = payload["library_row_fields"]
    travel_index = fields.index("travel_element")
    expected_fetchable_count = sum(1 for row in library.rows if row.is_available_for_fetch)

    assert len(payload["library_rows"]) == expected_fetchable_count
    assert payload["library_status"] == f"Local Excel Library ({expected_fetchable_count} fetchable lines)."
    assert any(
        "Check in to your accommodation" in str(row["v"].get(str(travel_index), ""))
        for row in payload["library_rows"]
    )
    serialized_size = len(json.dumps(payload["library_rows"], ensure_ascii=False).encode("utf-8"))
    assert serialized_size < 2_000_000
