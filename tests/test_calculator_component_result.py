from __future__ import annotations

import json

from app_modules.calculator_component_result import parse_calculator_grid_result


def test_parse_calculator_grid_result_returns_action_and_state() -> None:
    raw = json.dumps(
        {
            "action": "download",
            "show_advanced": True,
            "number_of_pax": 14,
            "client_state_revision": "abc123",
            "request_id": "request-1",
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
    assert result.state.number_of_pax == 14
    assert result.client_state_revision == "abc123"
    assert result.request_id == "request-1"
    assert result.state.rows[0].travel_element == "Oslo hotel"
    assert result.state.rows[0].supplier_commission == 0.15


def test_parse_calculator_grid_result_ignores_unknown_actions() -> None:
    assert parse_calculator_grid_result('{"action": "bad", "rows": []}', "Trip") is None
    assert parse_calculator_grid_result(None, "Trip") is None


def test_parse_calculator_grid_result_accepts_synchronized_navigation_actions() -> None:
    result = parse_calculator_grid_result(
        '{"action":"close","number_of_pax":"2.5","client_has_validation_errors":true,"rows":[]}',
        "Trip",
    )

    assert result is not None
    assert result.action == "close"
    assert result.state.number_of_pax == "2.5"
    assert result.client_has_validation_errors is True


def test_parse_calculator_grid_result_normalizes_whole_number_pax_text() -> None:
    result = parse_calculator_grid_result('{"action":"sync","number_of_pax":"2.0","rows":[]}', "Trip")

    assert result is not None
    assert result.state.number_of_pax == 2


def test_parse_calculator_grid_result_accepts_excel_upload_payload() -> None:
    result = parse_calculator_grid_result(
        '{"action":"open_excel","rows":[],"upload_filename":"Oslo.xlsx","upload_content_base64":"eGxzeA=="}',
        "Current Trip",
    )

    assert result is not None
    assert result.action == "open_excel"
    assert result.upload_filename == "Oslo.xlsx"
    assert result.upload_content_base64 == "eGxzeA=="


def test_browser_result_preserves_canonical_formula_overrides() -> None:
    result = parse_calculator_grid_result(
        json.dumps(
            {
                "action": "sync",
                "rows": [
                    {
                        "row_id": "1",
                        "supplier_commission": "30",
                        "gp_percent_override": 0.3,
                        "net_price_override": "=1/3",
                    },
                    {
                        "row_id": "2",
                        "supplier_commission": "=15+5",
                        "gp_percent_override": "=1/3",
                    },
                ],
            }
        ),
        "Trip",
    )

    assert result is not None
    first, second = result.state.rows
    assert first.supplier_commission == 0.3
    assert first.gp_percent_override == 0.3
    assert first.net_price_override == "=1/3"
    assert second.supplier_commission == 0.2
    assert second.gp_percent_override == "=1/3"
