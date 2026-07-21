from __future__ import annotations

from calculator.library_browser import (
    LocalLibraryBrowserFilters,
    filter_local_library_rows,
    local_library_city,
    local_library_filter_options,
    paginate_local_library_rows,
)
from calculator.library_model import LocalLibraryRow


def _rows() -> tuple[LocalLibraryRow, ...]:
    return (
        LocalLibraryRow(
            library_id="general_1",
            source_sheet="General",
            source_row=7,
            country="FI",
            category="Arrival",
            type="Arrival",
            supplier="",
            travel_element="Helsinki: Welcome to Finland",
            supplier_currency="EUR",
            sales_currency="EUR",
        ),
        LocalLibraryRow(
            library_id="activity_1",
            source_sheet="Activities",
            source_row=12,
            country="NO",
            category="Activity",
            type="Activity",
            supplier="Fjord Guide",
            travel_element="Bergen: Guided fjord walk",
            comments="Private departure",
            supplier_currency="NOK",
            sales_currency="EUR",
        ),
        LocalLibraryRow(
            library_id="deleted_1",
            source_sheet="Hotels",
            source_row=9,
            country="NO",
            type="Hotel",
            supplier="Old Hotel",
            travel_element="Oslo: Old Hotel",
            is_deleted=True,
        ),
    )


def test_city_uses_travel_element_prefix() -> None:
    assert local_library_city(_rows()[1]) == "Bergen"
    assert local_library_city(LocalLibraryRow(travel_element="No destination prefix")) == ""


def test_filter_options_cover_required_fields_and_ignore_deleted_rows() -> None:
    options = local_library_filter_options(_rows())

    assert options["worksheet"] == ("Activities", "General")
    assert options["country"] == ("FI", "NO")
    assert options["city"] == ("Bergen", "Helsinki")
    assert options["row_type"] == ("Activity", "Arrival")
    assert options["supplier"] == ("Fjord Guide",)
    assert options["currency"] == ("EUR", "NOK")


def test_required_filters_are_combined_and_case_insensitive() -> None:
    filters = LocalLibraryBrowserFilters(
        worksheet="activities",
        country="no",
        city="bergen",
        row_type="activity",
        supplier="fjord guide",
        currency="eur",
    )

    result = filter_local_library_rows(_rows(), filters)

    assert [row.library_id for row in result] == ["activity_1"]


def test_currency_filter_matches_supplier_or_sales_currency() -> None:
    nok = filter_local_library_rows(_rows(), LocalLibraryBrowserFilters(currency="NOK"))
    eur = filter_local_library_rows(_rows(), LocalLibraryBrowserFilters(currency="EUR"))

    assert [row.library_id for row in nok] == ["activity_1"]
    assert [row.library_id for row in eur] == ["general_1", "activity_1"]


def test_free_text_search_covers_record_content_and_identity() -> None:
    by_comment = filter_local_library_rows(_rows(), LocalLibraryBrowserFilters(query="private departure"))
    by_id = filter_local_library_rows(_rows(), LocalLibraryBrowserFilters(query="activity_1"))

    assert [row.library_id for row in by_comment] == ["activity_1"]
    assert [row.library_id for row in by_id] == ["activity_1"]


def test_browser_search_uses_canonical_nordic_normalization() -> None:
    rows = (
        LocalLibraryRow(
            library_id="flam_1",
            source_sheet="Activities",
            type="Activity",
            travel_element="Flåm: Nærøyfjord cruise",
        ),
    )

    result = filter_local_library_rows(rows, LocalLibraryBrowserFilters(query="Flam Naeroyfjord"))

    assert [row.library_id for row in result] == ["flam_1"]


def test_pagination_is_bounded_and_clamps_requested_page() -> None:
    rows = tuple(LocalLibraryRow(library_id=f"row_{index}") for index in range(12))

    middle = paginate_local_library_rows(rows, page_number=2, page_size=5)
    beyond = paginate_local_library_rows(rows, page_number=99, page_size=5)

    assert [row.library_id for row in middle.rows] == [f"row_{index}" for index in range(5, 10)]
    assert middle.page_count == 3
    assert middle.total_rows == 12
    assert beyond.page_number == 3
    assert [row.library_id for row in beyond.rows] == ["row_10", "row_11"]


def test_record_detail_groups_cover_every_stored_field() -> None:
    from dataclasses import fields

    from tests.support.streamlit_stub import install_streamlit_stub

    install_streamlit_stub()
    from app_modules.local_library_browser_ui import _detail_groups

    grouped_fields = {
        field_name
        for group in _detail_groups(LocalLibraryRow())
        for field_name in group
    }

    assert grouped_fields == {field.name for field in fields(LocalLibraryRow)}


def test_read_only_browser_renders_one_bounded_page(monkeypatch) -> None:
    from types import SimpleNamespace

    from tests.support.streamlit_stub import SessionState, install_streamlit_stub

    install_streamlit_stub()
    import app_modules.local_library_browser_ui as browser_ui
    from calculator.library_store import LocalLibraryReadResult

    class Column:
        def selectbox(self, label, options, **kwargs):
            values = tuple(options)
            if label == "Rows per page":
                return 50
            return values[0]

        def number_input(self, label, **kwargs):
            return 1

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    captured = {"tables": []}
    fake = SimpleNamespace(
        session_state=SessionState(),
        subheader=lambda *args, **kwargs: None,
        text_input=lambda *args, **kwargs: "",
        columns=lambda spec, **kwargs: tuple(Column() for _ in range(spec if isinstance(spec, int) else len(spec))),
        caption=lambda *args, **kwargs: None,
        info=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
        dataframe=lambda data, **kwargs: captured["tables"].append(data),
        selectbox=lambda label, options, **kwargs: tuple(options)[0],
        expander=lambda *args, **kwargs: Expander(),
    )
    monkeypatch.setattr(browser_ui, "st", fake)
    rows = tuple(
        LocalLibraryRow(
            library_id=f"row_{index}",
            source_sheet="Activities",
            source_row=index + 7,
            country="NO",
            type="Activity",
            travel_element=f"Bergen: Activity {index}",
        )
        for index in range(75)
    )

    browser_ui.render_local_library_browser(
        LocalLibraryReadResult(rows=rows, source="local_excel", read_only=True)
    )

    assert len(captured["tables"][0]) == 50
    assert fake.session_state["local_library_browser_selected_record"] == "row_0"
