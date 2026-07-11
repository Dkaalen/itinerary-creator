"""Commercial add-on extraction for group-tour packages."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from itinerary_domain.group_tour_master_rows import _master_title
from itinerary_domain.group_tour_models import GroupTourCommercialItem
from itinerary_domain.group_tour_row_helpers import _itinerary_day_number, _row_text, _row_type, _source_row_id
from itinerary_domain.group_tour_text import _clean, _int, _number_text
from text_polish import polish_title

def _commercial_status(master: Mapping[str, Any], day_rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    # An identified package with package-day rows is the booked product even if
    # generic parsing saw words such as "optional" inside a later Not Included
    # section. Optional upgrades are represented by their own commercial rows.
    if day_rows:
        return "included", "group_tour_master_with_package_days"
    source = _master_title(_row_text(master), master).casefold()
    units = _int(master.get("units"))
    if re.search(r"\b(optional|upgrade|add[- ]?on)\b", source) and units <= 0:
        return "optional", "group_tour_master_marked_optional"
    explicit = _clean(master.get("commercial_status")).casefold()
    if explicit in {"included", "optional", "self_arranged", "excluded"}:
        return explicit, _clean(master.get("commercial_reason")) or "source_commercial_status"
    return "included", "group_tour_master_product"


def _commercial_item(row: Mapping[str, Any], source_name: str) -> GroupTourCommercialItem | None:
    row_type = _row_type(row)
    category_map = {
        "transfer package": "transfer_package",
        "activity upgrade": "activity_upgrade",
        "single supplement fee": "single_supplement",
        "extra hotel night": "extra_hotel_night",
    }
    category = category_map.get(row_type.casefold())
    if not category:
        return None
    source = _row_text(row)
    title = _clean(row.get("title") or row.get("travel_element") or row.get("original_title") or source)
    mandatory_condition = ""
    if category == "single_supplement" and re.search(r"mandatory\s+for\s+solo", source, re.I):
        mandatory_condition = "Mandatory for solo travelers"
    units = _int(row.get("units"))
    selected = units > 0 or _clean(row.get("commercial_status")).casefold() == "included"
    return GroupTourCommercialItem(
        category=category,
        itinerary_day_number=_itinerary_day_number(row),
        title=polish_title(title),
        optional=not selected,
        selected=selected,
        mandatory_condition=mandatory_condition,
        unit_price=_number_text(row.get("sales_p_per_unit") or row.get("gross_p_per_unit") or row.get("unit_price")),
        total_price=_number_text(row.get("price") or row.get("gross_p") or row.get("total_price")),
        currency=_clean(row.get("sales_curr") or row.get("supp_curr") or row.get("currency")),
        source_url=_clean(row.get("url")),
        source_row_id=_source_row_id(row, source_name),
        source_text=source,
    )
