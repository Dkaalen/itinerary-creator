"""Canonical Norway in a Nutshell product contract.

Norway in a Nutshell is a compound route product made up of rail, fjord-cruise
and road legs.  It must not be reduced to a generic train/cruise title by
renderers.  This module owns the product-level identity, route endpoints,
ordered legs and source/commercial metadata.  Low-level source parsing remains
in :mod:`itinerary_generation.nutshell_parsing`.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping

from place_aliases import canonicalize_place_name
from text_polish import polish_title

from itinerary_generation.nutshell_parsing import (
    NUTSHELL_ROUTE_PLACES,
    _is_norway_in_a_nutshell_text,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
    should_preserve_nutshell_origin_label,
)

NUTSHELL_CANONICAL_FAMILY = "norway_in_a_nutshell"
NUTSHELL_PRODUCT_NAME = "Norway in a Nutshell"
NUTSHELL_PRODUCT_TYPE = "scenic_route"
NUTSHELL_CONTRACT_KIND = "norway_in_a_nutshell_journey"
NUTSHELL_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class NutshellLeg:
    """One source-owned leg within a Norway in a Nutshell journey."""

    origin: str
    destination: str
    mode: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    source_text: str = ""

    @property
    def as_metadata(self) -> dict[str, str]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "mode": self.mode,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "source_text": self.source_text,
        }

    @property
    def as_legacy_route_leg(self) -> dict[str, str]:
        """Return the shape used by existing generic transport consumers."""

        return {
            key: value
            for key, value in {
                "departure_time": self.departure_time,
                "origin": self.origin,
                "arrival_time": self.arrival_time,
                "destination": self.destination,
                "mode": self.mode,
            }.items()
            if value
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "NutshellLeg":
        return cls(
            origin=_clean_place(value.get("origin", "")),
            destination=_clean_place(value.get("destination", "")),
            mode=str(value.get("mode", "") or "").strip(),
            departure_time=str(value.get("departure_time", "") or "").strip(),
            arrival_time=str(value.get("arrival_time", "") or "").strip(),
            source_text=str(value.get("source_text", "") or "").strip(),
        )


@dataclass(frozen=True)
class NutshellJourney:
    """Canonical product-level representation for Norway in a Nutshell."""

    origin: str = ""
    destination: str = ""
    client_title: str = NUTSHELL_PRODUCT_NAME
    direction: str = ""
    route_points: tuple[str, ...] = ()
    legs: tuple[NutshellLeg, ...] = ()
    supplier_includes: tuple[str, ...] = ()
    included_services: tuple[str, ...] = ()
    journey_time: str = ""
    travel_date: str = ""
    commercial_status: str = ""
    commercial_reason: str = ""
    source_row_ids: tuple[str, ...] = ()
    source_title: str = ""
    confidence: str = "strong"
    variant_tags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def canonical_family(self) -> str:
        return NUTSHELL_CANONICAL_FAMILY

    @property
    def product_name(self) -> str:
        return NUTSHELL_PRODUCT_NAME

    @property
    def product_type(self) -> str:
        return NUTSHELL_PRODUCT_TYPE

    @property
    def as_metadata(self) -> dict[str, Any]:
        return {
            "kind": NUTSHELL_CONTRACT_KIND,
            "schema_version": NUTSHELL_CONTRACT_VERSION,
            "canonical_family": self.canonical_family,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "origin": self.origin,
            "destination": self.destination,
            "client_title": self.client_title,
            "direction": self.direction,
            "route_points": list(self.route_points),
            "legs": [leg.as_metadata for leg in self.legs],
            "supplier_includes": list(self.supplier_includes),
            "included_services": list(self.included_services),
            "journey_time": self.journey_time,
            "travel_date": self.travel_date,
            "commercial_status": self.commercial_status,
            "commercial_reason": self.commercial_reason,
            "source_row_ids": list(self.source_row_ids),
            "source_title": self.source_title,
            "confidence": self.confidence,
            "variant_tags": list(self.variant_tags),
            "warnings": list(self.warnings),
        }

    @property
    def legacy_route_legs(self) -> tuple[dict[str, str], ...]:
        return tuple(leg.as_legacy_route_leg for leg in self.legs)

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> "NutshellJourney":
        if value.get("kind") != NUTSHELL_CONTRACT_KIND:
            raise ValueError("Not a Norway in a Nutshell domain contract")
        version = int(value.get("schema_version", 0) or 0)
        if version != NUTSHELL_CONTRACT_VERSION:
            raise ValueError(f"Unsupported Norway in a Nutshell contract version: {version}")
        return cls(
            origin=_clean_place(value.get("origin", "")),
            destination=_clean_place(value.get("destination", "")),
            client_title=str(value.get("client_title", "") or NUTSHELL_PRODUCT_NAME),
            direction=str(value.get("direction", "") or ""),
            route_points=_clean_places(value.get("route_points", ())),
            legs=tuple(
                leg
                for leg in (NutshellLeg.from_mapping(item) for item in value.get("legs", ()) if isinstance(item, Mapping))
                if leg.origin and leg.destination
            ),
            supplier_includes=_clean_strings(value.get("supplier_includes", ())),
            included_services=_clean_strings(value.get("included_services", ())),
            journey_time=str(value.get("journey_time", "") or ""),
            travel_date=str(value.get("travel_date", "") or ""),
            commercial_status=str(value.get("commercial_status", "") or ""),
            commercial_reason=str(value.get("commercial_reason", "") or ""),
            source_row_ids=_clean_strings(value.get("source_row_ids", ())),
            source_title=str(value.get("source_title", "") or ""),
            confidence=str(value.get("confidence", "strong") or "strong"),
            variant_tags=_clean_strings(value.get("variant_tags", ())),
            warnings=_clean_strings(value.get("warnings", ())),
        )


def _clean_place(value: Any) -> str:
    return canonicalize_place_name(polish_title(str(value or "").strip(" -:|.,")))


def _clean_strings(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        values = [values]
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _clean_places(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in values or ():
        place = _clean_place(value)
        if place and (not result or result[-1].lower() != place.lower()):
            result.append(place)
    return tuple(result)


def _row_source(row: Mapping[str, Any] | None, extra_source: str = "") -> str:
    values: list[str] = []
    normalized_values: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        if any(normalized == existing or normalized in existing for existing in normalized_values):
            return
        values.append(text)
        normalized_values.append(normalized)

    if row:
        # Preserve structured/newline-rich fields before flattened raw text.
        # Timetable rows depend on line boundaries, and adding ``raw`` first can
        # make the de-duplication guard discard the richer ``details`` value.
        for key in (
            "details",
            "description_raw",
            "description",
            "route",
            "subtitle",
            "original_title",
            "title",
            "raw_text",
            "raw",
        ):
            add(row.get(key, ""))
        includes = row.get("source_includes") or row.get("supplier_includes") or row.get("includes") or ()
        if isinstance(includes, str):
            add(includes)
        else:
            for item in includes:
                add(item)
    if not values:
        add(extra_source)
    return "\n".join(values)


def _activity_product(row: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not row:
        return {}
    product = row.get("activity_product")
    return product if isinstance(product, Mapping) else {}


def is_nutshell_row(row: Mapping[str, Any] | None) -> bool:
    """Return True when the row is already classified or explicitly identifiable."""

    product = _activity_product(row)
    family = str(product.get("canonical_family", "") or "")
    if family:
        return family == NUTSHELL_CANONICAL_FAMILY
    contract = product.get("domain_contract")
    if isinstance(contract, Mapping):
        return contract.get("kind") == NUTSHELL_CONTRACT_KIND
    return _is_norway_in_a_nutshell_text(_row_source(row))


def _title_endpoints(title: str) -> tuple[str, str]:
    value = str(title or "")
    city = NUTSHELL_ROUTE_PLACES
    full = re.search(
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+from\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        value,
        flags=re.IGNORECASE,
    )
    if full:
        return _clean_place(full.group("origin")), _clean_place(full.group("destination"))
    destination_only = re.search(
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+to\s+(?P<destination>{city})\b",
        value,
        flags=re.IGNORECASE,
    )
    if destination_only:
        return "", _clean_place(destination_only.group("destination"))
    return "", ""


def _direct_route_endpoints(source: str) -> tuple[str, str]:
    city = NUTSHELL_ROUTE_PLACES
    patterns = (
        rf"\|\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*\|",
        rf"^\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*\|\s*Norway\s+in\s+a\s+(?:Nutshell|Nuthsell)",
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        rf"^\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})(?=\s*[:|\-]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            continue
        origin = _clean_place(match.group("origin"))
        destination = _clean_place(match.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""


def _mode_from_supplier_item(item: str) -> str:
    lower = item.lower()
    if "flåm railway" in lower or "flam railway" in lower:
        return "Flåm Railway"
    if "bergen railway" in lower:
        return "Bergen Railway"
    if "voss railway" in lower:
        return "Voss Railway"
    if "fjord cruise" in lower:
        return "Fjord Cruise"
    if "scenic bus" in lower:
        return "Scenic Bus"
    if "coach" in lower:
        return "Coach"
    if "bus" in lower:
        return "Bus"
    if "railway" in lower or "train" in lower or "rail" in lower:
        return "Train"
    if "cruise" in lower:
        return "Cruise"
    return ""


def _supplier_legs(items: Iterable[str]) -> tuple[NutshellLeg, ...]:
    city = NUTSHELL_ROUTE_PLACES
    legs: list[NutshellLeg] = []
    for item in items:
        text = str(item or "").strip()
        match = re.search(
            rf"\b(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        origin = _clean_place(match.group("origin"))
        destination = _clean_place(match.group("destination"))
        if not origin or not destination or origin.lower() == destination.lower():
            continue
        legs.append(
            NutshellLeg(
                origin=origin,
                destination=destination,
                mode=_mode_from_supplier_item(text),
                source_text=text,
            )
        )
    return tuple(legs)


def _mapping_legs(values: Any) -> tuple[NutshellLeg, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    legs: list[NutshellLeg] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        leg = NutshellLeg.from_mapping(value)
        if leg.origin and leg.destination and leg.origin.lower() != leg.destination.lower():
            legs.append(leg)
    return tuple(legs)



def _legs_from_points(points: tuple[str, ...]) -> tuple[NutshellLeg, ...]:
    if len(points) < 2:
        return ()
    return tuple(
        NutshellLeg(origin=points[index], destination=points[index + 1])
        for index in range(len(points) - 1)
        if points[index].lower() != points[index + 1].lower()
    )

def _ordered_points_from_legs(legs: tuple[NutshellLeg, ...]) -> tuple[tuple[str, ...], bool]:
    if not legs:
        return (), True
    points = [legs[0].origin]
    continuous = True
    for leg in legs:
        if points[-1].lower() != leg.origin.lower():
            continuous = False
            break
        points.append(leg.destination)
    return (tuple(points) if continuous else ()), continuous


def _direction(origin: str, destination: str) -> str:
    if not origin or not destination:
        return ""

    def token(value: str) -> str:
        clean = canonicalize_place_name(value).lower()
        clean = clean.replace("å", "a").replace("æ", "ae").replace("ø", "o")
        return re.sub(r"[^a-z0-9]+", "_", clean).strip("_")

    return f"{token(origin)}_to_{token(destination)}"


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
    """Build the canonical contract from source-owned row data.

    Known facts are preserved, unknown facts remain empty, and conflicting leg
    chains are recorded in ``warnings`` rather than silently repaired.
    """

    row: Mapping[str, Any] | None
    if isinstance(row_or_text, Mapping):
        row = row_or_text
        full_source = _row_source(row, source)
    else:
        row = None
        full_source = "\n".join(value for value in (str(row_or_text or ""), source) if value)

    product = _activity_product(row)
    family = str(product.get("canonical_family", "") or "")
    if family != NUTSHELL_CANONICAL_FAMILY and not _is_norway_in_a_nutshell_text(full_source):
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
    """Return the attached canonical contract, with a compatibility fallback.

    Normalized rows should always carry ``activity_product.domain_contract``.
    The fallback keeps older direct callers working without making renderers
    independently reconstruct product identity or route semantics.
    """

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
    "NUTSHELL_CANONICAL_FAMILY",
    "NUTSHELL_CONTRACT_KIND",
    "NUTSHELL_CONTRACT_VERSION",
    "NUTSHELL_PRODUCT_NAME",
    "NUTSHELL_PRODUCT_TYPE",
    "NutshellJourney",
    "NutshellLeg",
    "attach_nutshell_journey",
    "build_nutshell_journey",
    "has_nutshell_journey",
    "is_nutshell_row",
    "nutshell_journey_from_row",
    "resolve_nutshell_journey",
]
