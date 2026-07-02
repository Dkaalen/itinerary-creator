from __future__ import annotations

from calculator.library_model import LocalLibraryRow, SECTION_RECORD_TYPE
from calculator.library_search import library_result_label, library_result_preview, search_library_rows


def test_search_matches_expected_local_library_fields_and_ignores_deleted_rows() -> None:
    rows = (
        LocalLibraryRow(
            library_id="activity_1",
            country="FI",
            category="Activity",
            type="Activity",
            supplier="Finntastic Tours",
            travel_element="Helsinki walking tour",
            comments="Senate Square meeting point",
            url="https://example.com/helsinki",
        ),
        LocalLibraryRow(
            library_id="deleted_1",
            is_deleted=True,
            travel_element="Helsinki deleted row",
        ),
        LocalLibraryRow(
            library_id="hidden_1",
            is_fetchable=False,
            travel_element="Helsinki hidden row",
        ),
        LocalLibraryRow(
            library_id="section_1",
            record_type=SECTION_RECORD_TYPE,
            travel_element="Helsinki section row",
        ),
    )

    results = search_library_rows(rows, "helsinki senate")

    assert [result.row.library_id for result in results] == ["activity_1"]
    assert set(results[0].matched_fields) >= {"travel_element", "comments"}


def test_search_is_accent_insensitive_and_ranks_travel_element_matches_first() -> None:
    rows = (
        LocalLibraryRow(
            library_id="supplier_match",
            supplier="Tromso Adventures",
            travel_element="Generic northern lights chase",
        ),
        LocalLibraryRow(
            library_id="title_match",
            supplier="Vendor",
            travel_element="Tromsø northern lights chase",
        ),
    )

    results = search_library_rows(rows, "tromso")

    assert [result.row.library_id for result in results] == ["title_match", "supplier_match"]


def test_blank_search_returns_limited_active_rows_sorted_for_ui() -> None:
    rows = (
        LocalLibraryRow(library_id="b", country="NO", category="Transfer", travel_element="B transfer"),
        LocalLibraryRow(library_id="a", country="FI", category="Activity", travel_element="A activity"),
        LocalLibraryRow(library_id="c", country="SE", category="Hotel", travel_element="C hotel"),
    )

    results = search_library_rows(rows, "", limit=2)

    assert [result.row.library_id for result in results] == ["a", "b"]
    assert [result.score for result in results] == [0, 0]


def test_library_result_label_and_preview_are_compact_but_informative() -> None:
    row = LocalLibraryRow(
        library_id="lib_1",
        country="NO",
        category="Activity",
        supplier="Fjord Tours",
        travel_element="Oslo fjord cruise",
        gross_price_per_unit=100,
        supplier_currency="NOK",
        sales_price_per_unit=150,
        sales_currency="EUR",
        comments="Two-hour cruise",
        url="https://example.com",
    )

    assert library_result_label(row) == "NO · Activity · Fjord Tours — Oslo fjord cruise"
    preview = library_result_preview(row)
    assert "Oslo fjord cruise" in preview
    assert "Price/unit: 100 NOK" in preview
    assert "Sales/unit: 150 EUR" in preview
