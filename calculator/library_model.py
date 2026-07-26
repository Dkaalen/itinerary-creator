"""Data contracts for Local Library rows."""

from __future__ import annotations

from dataclasses import dataclass

from calculator.library_identity import local_library_source_identity

LOCAL_LIBRARY_SCHEMA_VERSION = "local_library_v1"
LOCAL_LIBRARY_SHEET_NAME = "Local Library"
LINE_RECORD_TYPE = "line"
SECTION_RECORD_TYPE = "section"


@dataclass(frozen=True)
class LocalLibraryColumn:
    """One column in the Local Library sheet schema."""

    field_name: str
    header: str


LOCAL_LIBRARY_COLUMNS: tuple[LocalLibraryColumn, ...] = (
    LocalLibraryColumn("schema_version", "schema_version"),
    LocalLibraryColumn("library_id", "library_id"),
    LocalLibraryColumn("is_deleted", "is_deleted"),
    LocalLibraryColumn("is_fetchable", "is_fetchable"),
    LocalLibraryColumn("record_type", "record_type"),
    LocalLibraryColumn("source_workbook", "source_workbook"),
    LocalLibraryColumn("source_sheet", "source_sheet"),
    LocalLibraryColumn("source_row", "source_row"),
    LocalLibraryColumn("country", "country"),
    LocalLibraryColumn("category", "category"),
    LocalLibraryColumn("search_text", "search_text"),
    LocalLibraryColumn("kalk_id", "ID"),
    LocalLibraryColumn("day", "Day"),
    LocalLibraryColumn("type", "Type"),
    LocalLibraryColumn("from_date", "From date"),
    LocalLibraryColumn("to_date", "To date"),
    LocalLibraryColumn("from_time", "From time"),
    LocalLibraryColumn("to_time", "To time"),
    LocalLibraryColumn("supplier", "Supplier"),
    LocalLibraryColumn("travel_element", "Travel element"),
    LocalLibraryColumn("manual_booking", "Manual booking?"),
    LocalLibraryColumn("status", "Status"),
    LocalLibraryColumn("comments", "Comments"),
    LocalLibraryColumn("non_refundable", "Non-refundable"),
    LocalLibraryColumn("refundable", "Refundable"),
    LocalLibraryColumn("url", "URL"),
    LocalLibraryColumn("gross_price_per_unit", "Gross P per unit"),
    LocalLibraryColumn("units", "Units"),
    LocalLibraryColumn("gross_price", "Gross P"),
    LocalLibraryColumn("supplier_commission", "Supp Comm"),
    LocalLibraryColumn("net_price", "Net P"),
    LocalLibraryColumn("supplier_currency", "Supp curr"),
    LocalLibraryColumn("supplier_x_rate", "X-rate"),
    LocalLibraryColumn("net_price_nok", "Net P NOK"),
    LocalLibraryColumn("sales_price_per_unit", "Sales P per unit"),
    LocalLibraryColumn("price", "Price"),
    LocalLibraryColumn("sales_currency", "Sales curr"),
    LocalLibraryColumn("sales_x_rate", "X-rate Sales"),
    LocalLibraryColumn("sales_price_nok_total", "Sales P NOK tot"),
    LocalLibraryColumn("gp_nok", "GP NOK"),
    LocalLibraryColumn("gp_percent", "GP %"),
    LocalLibraryColumn("vat25", "VAT25"),
    LocalLibraryColumn("vat15", "VAT15"),
    LocalLibraryColumn("vat12", "VAT12"),
    LocalLibraryColumn("vat0_domestic", "VAT0-D"),
    LocalLibraryColumn("vat0_international", "VAT0-I"),
    LocalLibraryColumn("formula_gross_total", "formula_gross_total"),
    LocalLibraryColumn("formula_net_price", "formula_net_price"),
    LocalLibraryColumn("formula_supplier_xrate", "formula_supplier_xrate"),
    LocalLibraryColumn("formula_net_nok", "formula_net_nok"),
    LocalLibraryColumn("formula_sales_unit_price", "formula_sales_unit_price"),
    LocalLibraryColumn("formula_price", "formula_price"),
    LocalLibraryColumn("formula_sales_xrate", "formula_sales_xrate"),
    LocalLibraryColumn("formula_sales_nok", "formula_sales_nok"),
    LocalLibraryColumn("formula_gp_nok", "formula_gp_nok"),
    LocalLibraryColumn("formula_gp_pct", "formula_gp_pct"),
    LocalLibraryColumn("created_at", "created_at"),
    LocalLibraryColumn("updated_at", "updated_at"),
    LocalLibraryColumn("updated_by", "updated_by"),
)

LOCAL_LIBRARY_HEADERS = tuple(column.header for column in LOCAL_LIBRARY_COLUMNS)
LOCAL_LIBRARY_FIELD_BY_HEADER = {column.header: column.field_name for column in LOCAL_LIBRARY_COLUMNS}
FORMULA_FIELD_NAMES = tuple(
    column.field_name for column in LOCAL_LIBRARY_COLUMNS if column.field_name.startswith("formula_")
)


@dataclass(frozen=True)
class LocalLibraryRow:
    """One normalized Local Library row independent of storage backend."""

    schema_version: str = LOCAL_LIBRARY_SCHEMA_VERSION
    library_id: str = ""
    is_deleted: bool = False
    is_fetchable: bool = True
    record_type: str = LINE_RECORD_TYPE
    source_workbook: str = ""
    source_sheet: str = ""
    source_row: int | None = None
    country: str = ""
    category: str = ""
    search_text: str = ""
    kalk_id: str = ""
    day: str = ""
    type: str = ""
    from_date: str = ""
    to_date: str = ""
    from_time: str = ""
    to_time: str = ""
    supplier: str = ""
    travel_element: str = ""
    manual_booking: bool = False
    status: str = ""
    comments: str = ""
    non_refundable: bool = False
    refundable: bool = False
    url: str = ""
    gross_price_per_unit: float = 0.0
    units: float = 0.0
    gross_price: float = 0.0
    supplier_commission: float = 0.0
    net_price: float = 0.0
    supplier_currency: str = "NOK"
    supplier_x_rate: float = 0.0
    net_price_nok: float = 0.0
    sales_price_per_unit: float | None = None
    price: float = 0.0
    sales_currency: str = "NOK"
    sales_x_rate: float = 0.0
    sales_price_nok_total: float = 0.0
    gp_nok: float = 0.0
    gp_percent: float = 0.0
    vat25: float = 0.0
    vat15: float = 0.0
    vat12: float = 0.0
    vat0_domestic: float = 0.0
    vat0_international: float = 0.0
    formula_gross_total: str = ""
    formula_net_price: str = ""
    formula_supplier_xrate: str = ""
    formula_net_nok: str = ""
    formula_sales_unit_price: str = ""
    formula_price: str = ""
    formula_sales_xrate: str = ""
    formula_sales_nok: str = ""
    formula_gp_nok: str = ""
    formula_gp_pct: str = ""
    created_at: str = ""
    updated_at: str = ""
    updated_by: str = ""

    @property
    def source_identity(self) -> str:
        """Return stable workbook provenance independent of display text."""

        return local_library_source_identity(self.__dict__)

    @property
    def is_available_for_fetch(self) -> bool:
        """Return whether this row should appear in calculator fetch search."""

        return self.record_type == LINE_RECORD_TYPE and self.is_fetchable and not self.is_deleted
