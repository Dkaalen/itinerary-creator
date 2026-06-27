"""Norway in a Nutshell journey builder."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_generation.nutshell_cleaning import _clean_place, _clean_places, _clean_strings
from itinerary_generation.nutshell_constants import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
)
from itinerary_generation.nutshell_model import NutshellJourney
from itinerary_generation.nutshell_parsing import (
    _is_norway_in_a_nutshell_text,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
    should_preserve_nutshell_origin_label,
    is_source_backed_nutshell_route_package,
)
from itinerary_generation.nutshell_route_parser import (
    _direct_route_endpoints,
    _direction,
    _legs_from_points,
    _mapping_legs,
    _ordered_points_from_legs,
    _supplier_legs,
    _title_endpoints,
)
from itinerary_generation.nutshell_source import _activity_product, _row_source, is_nutshell_row


def _source_row_ids(row: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not row:
        return ()
    values: list[str] = []
    row_ids = row.get("source_row_ids")
    if isinstance(row_ids, (list, tuple, set)):
        values.extend(str(value) for value in row_ids if value)
    row_id = row.get("row_id")
    if row_id:
        values.append(str(row_id))
    return _clean_strings(values)


def _client_title(source: str, origin: str, destination: str, explicit_title: str = "") -> str:
    explicit_origin, explicit_destination = _title_endpoints(explicit_title)
    if explicit_origin and explicit_destination:
        return f"{NUTSHELL_PRODUCT_NAME} from {explicit_origin} to {explicit_destination}"
    if explicit_destination and not explicit_origin:
        return f"{NUTSHELL_PRODUCT_NAME} to {explicit_destination}"
    if origin and destination and should_preserve_nutshell_origin_label(source, origin, destination):
        return f"{NUTSHELL_PRODUCT_NAME} from {origin} to {destination}"
    if destination:
        return f"{NUTSHELL_PRODUCT_NAME} to {destination}"
    return NUTSHELL_PRODUCT_NAME


def build_nutshell_journey(
    row_or_text: Mapping[str, Any] | str | None,
    *,
    source: str = "",
    source_title: str = "",
    fallback_origin: str = "",
    fallback_destination: str = "",
) -> NutshellJourney | None:
    """Build the canonical contract from source-owned row data."""

    row: Mapping[str, Any] | None
    if isinstance(row_or_text, Mapping):
        row = row_or_text
        full_source = _row_source(row, source)
    else:
        row = None
        full_source = "\n".join(value for value in (str(row_or_text or ""), source) if value)

    product = _activity_product(row)
    family = str(product.get("canonical_family", "") or "")
    if (
        family != NUTSHELL_CANONICAL_FAMILY
        and not _is_norway_in_a_nutshell_text(full_source)
        and not is_source_backed_nutshell_route_package(full_source)
    ):
        return None

    explicit_candidates = (
        str(product.get("display_title", "") or ""),
        explicit_norway_nutshell_title(full_source),
        source_title,
        str(row.get("title", "") if row else ""),
    )
    explicit_title = ""
    origin = ""
    destination = ""
    for candidate in explicit_candidates:
        candidate_origin, candidate_destination = _title_endpoints(candidate)
        if not candidate_origin and not candidate_destination:
            continue
        origin, destination = candidate_origin, candidate_destination
        explicit_title = (
            f"{NUTSHELL_PRODUCT_NAME} from {origin} to {destination}"
            if origin and destination
            else f"{NUTSHELL_PRODUCT_NAME} to {destination}"
        )
        break

    if not origin or not destination:
        direct_origin, direct_destination = _direct_route_endpoints(full_source)
        origin = origin or direct_origin
        destination = destination or direct_destination

    parsed_timetable_legs = _mapping_legs(extract_norway_nutshell_route_legs(full_source))
    supplier_includes = tuple(extract_norway_nutshell_supplier_includes(full_source))
    if not supplier_includes and row:
        supplier_includes = tuple(extract_norway_nutshell_supplier_includes(row))
    parsed_supplier_legs = _supplier_legs(supplier_includes)
    product_legs = _mapping_legs(product.get("route_legs", ()))
    row_legs = _mapping_legs(row.get("route_legs", ()) if row else ())
    extracted_points = _clean_places(extract_norway_nutshell_route_points(full_source))
    legs = (
        parsed_timetable_legs
        or parsed_supplier_legs
        or product_legs
        or row_legs
        or _legs_from_points(extracted_points)
    )

    leg_points, continuous = _ordered_points_from_legs(legs)

    if not origin and leg_points:
        origin = leg_points[0]
    if not destination and leg_points:
        destination = leg_points[-1]
    if not origin and extracted_points:
        origin = extracted_points[0]
    if not destination and extracted_points:
        destination = extracted_points[-1]

    origin = origin or _clean_place(fallback_origin)
    destination = destination or _clean_place(fallback_destination)

    warnings: list[str] = []
    if legs and not continuous:
        warnings.append("route_leg_discontinuity")
    if leg_points and origin and destination:
        if leg_points[0].lower() != origin.lower() or leg_points[-1].lower() != destination.lower():
            warnings.append("route_endpoint_conflict")

    if leg_points and not warnings:
        route_points = leg_points
    elif origin and destination:
        route_points = (origin, destination)
    elif extracted_points:
        route_points = extracted_points
    else:
        route_points = tuple(value for value in (origin, destination) if value)

    included_services = _clean_strings(row.get("includes", ()) if row else ())
    source_title_value = str(
        source_title
        or (row.get("original_title", "") if row else "")
        or product.get("source_title", "")
        or explicit_title
        or NUTSHELL_PRODUCT_NAME
    ).strip()
    confidence = str(product.get("confidence", "strong") or "strong")
    variant_tags = _clean_strings(product.get("variant_tags", ()))
    existing_warnings = _clean_strings(product.get("warnings", ()))
    warnings = list(dict.fromkeys((*existing_warnings, *warnings)))

    return NutshellJourney(
        origin=origin,
        destination=destination,
        client_title=_client_title(full_source, origin, destination, explicit_title),
        direction=_direction(origin, destination),
        route_points=route_points,
        legs=legs,
        supplier_includes=supplier_includes,
        included_services=included_services,
        journey_time=str(row.get("time", "") if row else ""),
        travel_date=str(row.get("start_date", "") if row else ""),
        commercial_status=str(row.get("commercial_status", "") if row else ""),
        commercial_reason=str(row.get("commercial_reason", "") if row else ""),
        source_row_ids=_source_row_ids(row),
        source_title=source_title_value,
        confidence=confidence,
        variant_tags=variant_tags,
        warnings=tuple(warnings),
    )


def nutshell_journey_from_row(row: Mapping[str, Any] | None) -> NutshellJourney | None:
    """Read an attached contract without re-parsing source text."""

    product = _activity_product(row)
    contract = product.get("domain_contract")
    if not isinstance(contract, Mapping):
        return None
    try:
        return NutshellJourney.from_metadata(contract)
    except (TypeError, ValueError):
        return None


def resolve_nutshell_journey(row: Mapping[str, Any] | None) -> NutshellJourney | None:
    """Return the attached canonical contract, with a compatibility fallback."""

    journey = nutshell_journey_from_row(row)
    if journey is not None:
        return journey
    if not is_nutshell_row(row):
        return None
    return build_nutshell_journey(row)


def has_nutshell_journey(rows: Iterable[Mapping[str, Any]]) -> bool:
    """Return whether any normalized row represents the Nutshell product."""

    return any(resolve_nutshell_journey(row) is not None for row in rows or ())


def attach_nutshell_journey(row: dict[str, Any]) -> dict[str, Any]:
    """Attach one normalized contract to an already-normalized row."""

    journey = build_nutshell_journey(row)
    if journey is None:
        return row

    product = dict(_activity_product(row))
    product.update(
        {
            "canonical_family": NUTSHELL_CANONICAL_FAMILY,
            "product_type": NUTSHELL_PRODUCT_TYPE,
            "display_title": journey.client_title,
            "confidence": journey.confidence,
            "source_title": product.get("source_title") or journey.source_title,
            "variant_tags": list(journey.variant_tags),
            "route_legs": [dict(leg) for leg in journey.legacy_route_legs],
            "warnings": list(journey.warnings),
            "domain_contract": journey.as_metadata,
        }
    )
    row["activity_product"] = product
    row["title"] = journey.client_title
    row["route_legs"] = [dict(leg) for leg in journey.legacy_route_legs]
    return row


__all__ = [
    "_clean_place",
    "_clean_places",
    "_clean_strings",
    "_client_title",
    "_source_row_ids",
    "attach_nutshell_journey",
    "build_nutshell_journey",
    "has_nutshell_journey",
    "nutshell_journey_from_row",
    "resolve_nutshell_journey",
]
