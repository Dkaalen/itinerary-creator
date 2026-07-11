"""Parser/normalizer integration for canonical multi-day group tours.

This module owns the boundary between supplier-shaped rows and the renderer-
neutral :mod:`itinerary_generation.group_tour_domain` contract.  It deliberately
keeps package days, independent hotels, and commercial add-ons as separate row
classes while linking them through stable metadata.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Iterable, Mapping

from itinerary_generation.group_tour_domain import (
    GroupTourPackage,
    annotate_group_tour_rows,
    group_tour_day_from_row,
    group_tour_package_from_row,
)
from itinerary_generation.group_tour_orphan_days import annotate_orphan_group_tour_days

_GROUP_TOUR_COMMERCIAL_TYPES = {
    "activity upgrade": "activity_upgrade",
    "transfer package": "transfer_package",
    "single supplement fee": "single_supplement",
    "extra hotel night": "extra_hotel_night",
}


def prepare_group_tour_source_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_name: str = "",
) -> list[dict[str, Any]]:
    """Hydrate workbook-shaped rows before normal normalization.

    The Iceland standard-itinerary workbook stores the client text in
    ``travel_element`` instead of the parser's usual ``title``/``details``
    fields.  Keeping this adaptation at the input boundary lets the ordinary
    hotel, transfer, arrival and departure normalizers work without teaching
    renderers about spreadsheet columns.

    Rows already produced by the text parser are returned unchanged apart from
    receiving a deterministic source id when one is missing.
    """

    prepared: list[dict[str, Any]] = []
    safe_source = re.sub(r"[^a-z0-9]+", "-", str(source_name or "source").casefold()).strip("-") or "source"
    for index, source_row in enumerate(rows or ()):  # pragma: no branch - tiny deterministic adapter
        row = deepcopy(dict(source_row))
        source_text = str(row.get("travel_element") or "").strip()
        if not str(row.get("row_id") or "").strip():
            source_index = row.get("excel_row") or row.get("line_number") or index + 1
            row["row_id"] = f"{safe_source}-row-{source_index}"

        if source_text:
            row.setdefault("raw", source_text)
            row.setdefault("original_title", source_text)
            row.setdefault("details", source_text)
            row.setdefault("title", source_text)

            row_type = _row_type(row).casefold()
            # Package-day text begins with ``Day N:``; that prefix is not a
            # destination.  Other workbook rows follow ``City: service`` and
            # can safely seed the standard city field before canonicalisation.
            if row_type != "group tour" and not str(row.get("city") or "").strip():
                match = re.match(r"^([^:|]{2,60})\s*:\s*", source_text)
                if match and not re.fullmatch(r"day\s*\d+", match.group(1).strip(), flags=re.IGNORECASE):
                    row["city"] = match.group(1).strip()
        prepared.append(row)
    return prepared


def _row_type(row: Mapping[str, Any]) -> str:
    return str(row.get("effective_type") or row.get("type") or "").strip()


def _selected_commercial_row(row: Mapping[str, Any]) -> bool:
    status = str(row.get("commercial_status") or "").strip().casefold()
    if status == "included":
        return True
    try:
        return float(str(row.get("units") or "0").replace(",", ".")) > 0
    except (TypeError, ValueError):
        return False


def _is_totals_artifact(row: Mapping[str, Any]) -> bool:
    """Return True for the worksheet's non-itinerary totals marker row.

    The Iceland standard workbook ends each sheet with an ``id=Totals`` row
    whose itinerary cells contain only ``x``.  It is source bookkeeping, not a
    client or commercial itinerary row.  Runtime text inputs without that exact
    marker are left untouched.
    """

    return (
        str(row.get("id") or "").strip().casefold() == "totals"
        and _row_type(row).casefold() == "x"
        and str(row.get("travel_element") or row.get("details") or "").strip().casefold() == "x"
    )


def integrate_group_tour_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    season: str = "",
    source_name: str = "",
) -> list[dict[str, Any]]:
    """Attach one canonical package contract and stable row roles.

    The function is intentionally non-rendering.  It provides structured facts
    for later consumers without turning package-day rows into ordinary
    activities or merging pre/post-tour hotels into package accommodation.
    """

    prepared = [deepcopy(dict(row)) for row in rows or () if not _is_totals_artifact(row)]
    annotated = annotate_group_tour_rows(prepared, season=season, source_name=source_name)

    master_row = next((row for row in annotated if group_tour_package_from_row(row) is not None), None)
    package: GroupTourPackage | None = group_tour_package_from_row(master_row)
    if package is None:
        return annotate_orphan_group_tour_days(annotated, source_name=source_name)

    commercial_by_source_id = {item.source_row_id: item for item in package.commercial_items}
    package_context = {
        "package_id": package.package_id,
        "title": package.title,
        "season": package.season,
        "duration_days": package.duration_days,
        "itinerary_start_day": package.itinerary_start_day,
        "itinerary_end_day": package.itinerary_end_day,
        "meeting_point": package.meeting_point,
        "pickup_time": package.pickup_time,
        "group_style": package.group_style,
        "commercial_status": package.commercial_status,
        "accommodation_policy": package.accommodation_policy.as_metadata,
        "warnings": list(package.warnings),
    }
    for row in annotated:
        if row is master_row:
            row["group_tour_role"] = "package_master"
            row["group_tour_package_context"] = package_context
            row["group_tour_season"] = package.season
            row["group_tour_duration_days"] = package.duration_days
            continue

        segment = group_tour_day_from_row(row)
        if segment is not None:
            row["group_tour_role"] = "day_segment"
            row["group_tour_package_context"] = package_context
            row["group_tour_package_day"] = segment.package_day_number
            row["group_tour_itinerary_day"] = segment.itinerary_day_number
            row["group_tour_season"] = package.season
            continue

        row_type = _row_type(row).casefold()
        category = _GROUP_TOUR_COMMERCIAL_TYPES.get(row_type)
        if not category:
            # Independent hotels, transfers, arrivals, departures, and leisure
            # rows intentionally remain unlinked.
            continue

        source_id = str(row.get("row_id") or "").strip()
        item = commercial_by_source_id.get(source_id)
        row["group_tour_role"] = "commercial_item"
        row["group_tour_commercial_category"] = category
        row["group_tour_semantic_type"] = {
            "activity_upgrade": "Activity",
            "transfer_package": "Transfer",
            "extra_hotel_night": "Hotel",
            "single_supplement": "Commercial Fee",
        }[category]
        row["related_group_tour_package_id"] = package.package_id
        selected = item.selected if item is not None else _selected_commercial_row(row)
        row["group_tour_commercial_selected"] = selected
        if selected:
            row["is_optional"] = False
            row["commercial_status"] = "included"
            row["commercial_reason"] = "group_tour_commercial_add_on_selected"
            if category == "activity_upgrade":
                row["effective_type"] = "Activity"
            elif category == "transfer_package":
                row["effective_type"] = "Transfer"
            elif category == "extra_hotel_night":
                row["effective_type"] = "Hotel"
        else:
            row["is_optional"] = True
            row["commercial_status"] = "optional"
            row["commercial_reason"] = "group_tour_commercial_add_on"

    return annotated


__all__ = ["integrate_group_tour_rows", "prepare_group_tour_source_rows"]
