from __future__ import annotations

import pytest

from calculator.library_search import LocalLibrarySearchContext, search_library_rows
from calculator.library_workbook import load_local_library_workbook


@pytest.mark.parametrize("row_type", ("Activity", "Transfer"))
@pytest.mark.parametrize(
    ("query", "origin"),
    (
        ("Oslo Norway in a Nutshell", "oslo"),
        ("Bergen Norway in a Nutshell", "bergen"),
        ("Flåm Norway in a Nutshell", "flåm"),
        ("Flam Norway in a Nutshell", "flåm"),
    ),
)
def test_bundled_nutshell_products_are_cross_type_fetchable(row_type: str, query: str, origin: str) -> None:
    library = load_local_library_workbook()
    results = search_library_rows(
        library.rows,
        query,
        context=LocalLibrarySearchContext(type=row_type, travel_element=query),
        limit=8,
    )

    transport_matches = [
        result.row
        for result in results
        if result.row.source_sheet == "Transport"
        and result.row.travel_element.casefold().startswith(f"{origin}:".casefold())
        and "Norway in a Nutshell" in result.row.travel_element
    ]
    assert transport_matches, (row_type, query, [result.row.travel_element for result in results])


def test_nutshell_alias_does_not_merge_intentional_workbook_rows() -> None:
    library = load_local_library_workbook()
    query = "Bergen Norway in a Nutshell"
    results = search_library_rows(
        library.rows,
        query,
        context=LocalLibrarySearchContext(type="Transfer", travel_element=query),
        limit=8,
    )
    identities = [
        (result.row.source_sheet, result.row.source_row, result.row.library_id)
        for result in results
        if "Norway in a Nutshell" in result.row.travel_element
    ]

    assert len(identities) >= 5
    assert len(identities) == len(set(identities))
