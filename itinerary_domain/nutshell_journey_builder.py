"""Norway in a Nutshell journey builder."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_domain.nutshell_cleaning import _clean_place, _clean_places, _clean_strings
from itinerary_domain.nutshell_constants import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
)
from itinerary_domain.nutshell_model import NutshellJourney
from itinerary_domain.nutshell_parsing import (
    _is_norway_in_a_nutshell_text,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
    should_preserve_nutshell_origin_label,
    is_source_backed_nutshell_route_package,
)
from itinerary_domain.nutshell_route_parser import (
    _direct_route_endpoints,
    _direction,
    _legs_from_points,
    _mapping_legs,
    _ordered_points_from_legs,
    _supplier_legs,
    _title_endpoints,
)
from itinerary_domain.nutshell_source import _activity_product, _row_source, is_nutshell_row


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


def _source_context(
    row_or_text: Mapping[str, Any] | str | None,
    source: str,
) -> tuple[Mapping[str, Any] | None, str]:
    if isinstance(row_or_text, Mapping):
        row = row_or_text
        return row, _row_source(row, source)
    return None, "\n".join(value for value in (str(row_or_text or ""), source) if value)


def _is_nutshell_candidate(product: Mapping[str, Any], full_source: str) -> bool:
    family = str(product.get("canonical_family", "") or "")
    return (
        family == NUTSHELL_CANONICAL_FAMILY
        or _is_norway_in_a_nutshell_text(full_source)
        or is_source_backed_nutshell_route_package(full_source)
    )


def _explicit_title_candidates(
    row: Mapping[str, Any] | None,
    product: Mapping[str, Any],
    full_source: str,
    source_title: str,
) -> tuple[str, ...]:
    return (
        str(product.get("display_title", "") or ""),
        explicit_norway_nutshell_title(full_source),
        source_title,
        str(row.get("title", "") if row else ""),
    )


def _resolve_explicit_endpoints(candidates: Iterable[str]) -> tuple[str, str, str]:
    for candidate in candidates:
        candidate_origin, candidate_destination = _title_endpoints(candidate)
        if not candidate_origin and not candidate_destination:
            continue
        explicit_title = (
            f"{NUTSHELL_PRODUCT_NAME} from {candidate_origin} to {candidate_destination}"
            if candidate_origin and candidate_destination
            else f"{NUTSHELL_PRODUCT_NAME} to {candidate_destination}"
        )
        return candidate_origin, candidate_destination, explicit_title
    return "", "", ""


def _resolve_route_legs(
    row: Mapping[str, Any] | None,
    product: Mapping[str, Any],
    full_source: str,
) -> tuple[tuple[Any, ...], tuple[str, ...], tuple[str, ...]]:
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
    return legs, supplier_includes, extracted_points


def _resolve_endpoints_from_route(
    origin: str,
    destination: str,
    leg_points: tuple[str, ...],
    extracted_points: tuple[str, ...],
    fallback_origin: str,
    fallback_destination: str,
) -> tuple[str, str]:
    if not origin and leg_points:
        origin = leg_points[0]
    if not destination and leg_points:
        destination = leg_points[-1]
    if not origin and extracted_points:
        origin = extracted_points[0]
    if not destination and extracted_points:
        destination = extracted_points[-1]
    return origin or _clean_place(fallback_origin), destination or _clean_place(fallback_destination)


def _route_points_and_warnings(
    origin: str,
    destination: str,
    legs: tuple[Any, ...],
    extracted_points: tuple[str, ...],
) -> tuple[tuple[str, ...], list[str]]:
    leg_points, continuous = _ordered_points_from_legs(legs)
    warnings: list[str] = []
    if legs and not continuous:
        warnings.append("route_leg_discontinuity")
    if leg_points and origin and destination:
        if leg_points[0].lower() != origin.lower() or leg_points[-1].lower() != destination.lower():
            warnings.append("route_endpoint_conflict")

    if leg_points and not warnings:
        return leg_points, warnings
    if origin and destination:
        return (origin, destination), warnings
    if extracted_points:
        return extracted_points, warnings
    return tuple(value for value in (origin, destination) if value), warnings


def _nutshell_source_title_value(
    row: Mapping[str, Any] | None,
    product: Mapping[str, Any],
    source_title: str,
    explicit_title: str,
) -> str:
    return str(
        source_title
        or (row.get("original_title", "") if row else "")
        or product.get("source_title", "")
        or explicit_title
        or NUTSHELL_PRODUCT_NAME
    ).strip()


def build_nutshell_journey(
    row_or_text: Mapping[str, Any] | str | None,
    *,
    source: str = "",
    source_title: str = "",
    fallback_origin: str = "",
    fallback_destination: str = "",
) -> NutshellJourney | None:
    """Build the canonical contract from source-owned row data."""

    row, full_source = _source_context(row_or_text, source)
    product = _activity_product(row)
    if not _is_nutshell_candidate(product, full_source):
        return None

    origin, destination, explicit_title = _resolve_explicit_endpoints(
        _explicit_title_candidates(row, product, full_source, source_title)
    )
    if not origin or not destination:
        direct_origin, direct_destination = _direct_route_endpoints(full_source)
        origin = origin or direct_origin
        destination = destination or direct_destination

    legs, supplier_includes, extracted_points = _resolve_route_legs(row, product, full_source)
    leg_points, _continuous = _ordered_points_from_legs(legs)
    origin, destination = _resolve_endpoints_from_route(
        origin,
        destination,
        leg_points,
        extracted_points,
        fallback_origin,
        fallback_destination,
    )
    route_points, route_warnings = _route_points_and_warnings(origin, destination, legs, extracted_points)

    included_services = _clean_strings(row.get("includes", ()) if row else ())
    existing_warnings = _clean_strings(product.get("warnings", ()))
    warnings = list(dict.fromkeys((*existing_warnings, *route_warnings)))

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
        source_title=_nutshell_source_title_value(row, product, source_title, explicit_title),
        confidence=str(product.get("confidence", "strong") or "strong"),
        variant_tags=_clean_strings(product.get("variant_tags", ())),
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
