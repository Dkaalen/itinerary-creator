"""Read-only fallback Local Library fixture rows."""

from __future__ import annotations

from calculator.library_model import LocalLibraryRow


_FALLBACK_ROWS: tuple[LocalLibraryRow, ...] = (
    LocalLibraryRow(
        library_id="fixture_oslo_hotel",
        country="NO",
        category="Hotel",
        type="Hotel",
        supplier="RateHawk",
        travel_element="Oslo: Check in to your accommodation",
        url="https://www.ratehawk.com/",
        supplier_currency="EUR",
        sales_currency="EUR",
        search_text="NO | Hotel | Oslo accommodation | RateHawk",
        updated_by="fixture",
    ),
    LocalLibraryRow(
        library_id="fixture_helsinki_walk",
        country="FI",
        category="Activity",
        type="Activity",
        supplier="Finntastic Tours",
        travel_element="Helsinki: A Finntastic Walking Tour",
        url="https://www.finntastictours.fi/#",
        gross_price_per_unit=25.0,
        units=1.0,
        supplier_currency="EUR",
        sales_currency="EUR",
        search_text="FI | Activity | Helsinki walking tour | Finntastic Tours",
        updated_by="fixture",
    ),
    LocalLibraryRow(
        library_id="fixture_self_transfer",
        country="NO",
        category="Transfer",
        type="Transfer",
        travel_element="Self transfer Hotel to Station",
        gross_price_per_unit=0.0,
        units=0.0,
        supplier_currency="NOK",
        sales_currency="NOK",
        search_text="NO | Transfer | Self transfer Hotel to Station",
        updated_by="fixture",
    ),
)


def fallback_library_rows() -> tuple[LocalLibraryRow, ...]:
    """Return bundled read-only rows for missing Local Library credentials."""

    return _FALLBACK_ROWS
