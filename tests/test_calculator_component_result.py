from __future__ import annotations

import json

from app_modules.calculator_component_result import parse_calculator_grid_result


def test_parse_calculator_grid_result_returns_action_and_state() -> None:
    raw = json.dumps(
        {
            "action": "download",
            "show_advanced": True,
            "client_state_revision": "abc123",
            "rows": [
                {
                    "row_id": "1",
                    "day": "Day 1",
                    "type": "Hotel",
                    "travel_element": "Oslo hotel",
                    "gross_price_per_unit": "200",
                    "units": "2",
                    "supplier_commission": "15",
                    "supplier_currency": "EUR",
                    "sales_currency": "EUR",
                }
            ],
        }
    )

    result = parse_calculator_grid_result(raw, "Trip")

    assert result is not None
    assert result.action == "download"
    assert result.show_advanced is True
    assert result.state.itinerary_name == "Trip"
    assert result.client_state_revision == "abc123"
    assert result.state.rows[0].travel_element == "Oslo hotel"
    assert result.state.rows[0].supplier_commission == 0.15


def test_parse_calculator_grid_result_ignores_unknown_actions() -> None:
    assert parse_calculator_grid_result('{"action": "bad", "rows": []}', "Trip") is None
    assert parse_calculator_grid_result(None, "Trip") is None
