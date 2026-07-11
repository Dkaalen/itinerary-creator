"""Norway in a Nutshell data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from itinerary_domain.nutshell_cleaning import _clean_place, _clean_places, _clean_strings
from itinerary_domain.nutshell_constants import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_CONTRACT_KIND,
    NUTSHELL_CONTRACT_VERSION,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
)


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


__all__ = ["NutshellJourney", "NutshellLeg"]
