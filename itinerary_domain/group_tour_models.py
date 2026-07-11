"""Dataclasses for the canonical group-tour package contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from itinerary_domain.group_tour_constants import (
    GROUP_TOUR_CANONICAL_FAMILY,
    GROUP_TOUR_CONTRACT_KIND,
    GROUP_TOUR_CONTRACT_VERSION,
    GROUP_TOUR_PRODUCT_TYPE,
)
from itinerary_domain.group_tour_text import _clean, _clean_strings, _int, _normalize_season

@dataclass(frozen=True)
class GroupTourAccommodationPolicy:
    """Package-level accommodation promise without inventing exact hotels."""

    included: bool = False
    nights: int = 0
    nights_inferred: bool = False
    room_basis: str = ""
    bathroom: str = ""
    meal_plan: str = ""
    exact_properties_confirmed: bool = False
    source_wording: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def as_metadata(self) -> dict[str, Any]:
        return {
            "included": self.included,
            "nights": self.nights,
            "nights_inferred": self.nights_inferred,
            "room_basis": self.room_basis,
            "bathroom": self.bathroom,
            "meal_plan": self.meal_plan,
            "exact_properties_confirmed": self.exact_properties_confirmed,
            "source_wording": list(self.source_wording),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any] | None) -> "GroupTourAccommodationPolicy":
        value = value or {}
        return cls(
            included=bool(value.get("included")),
            nights=max(0, _int(value.get("nights"))),
            nights_inferred=bool(value.get("nights_inferred")),
            room_basis=_clean(value.get("room_basis")),
            bathroom=_clean(value.get("bathroom")),
            meal_plan=_clean(value.get("meal_plan")),
            exact_properties_confirmed=bool(value.get("exact_properties_confirmed")),
            source_wording=_clean_strings(value.get("source_wording")),
            warnings=_clean_strings(value.get("warnings")),
        )


@dataclass(frozen=True)
class GroupTourCommercialItem:
    """Commercial or optional row related to, but not included in, the package."""

    category: str
    itinerary_day_number: int = 0
    title: str = ""
    optional: bool = True
    selected: bool = False
    mandatory_condition: str = ""
    unit_price: str = ""
    total_price: str = ""
    currency: str = ""
    source_url: str = ""
    source_row_id: str = ""
    source_text: str = ""

    @property
    def as_metadata(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "itinerary_day_number": self.itinerary_day_number,
            "title": self.title,
            "optional": self.optional,
            "selected": self.selected,
            "mandatory_condition": self.mandatory_condition,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "currency": self.currency,
            "source_url": self.source_url,
            "source_row_id": self.source_row_id,
            "source_text": self.source_text,
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> "GroupTourCommercialItem":
        return cls(
            category=_clean(value.get("category")),
            itinerary_day_number=max(0, _int(value.get("itinerary_day_number"))),
            title=_clean(value.get("title")),
            optional=bool(value.get("optional", True)),
            selected=bool(value.get("selected")),
            mandatory_condition=_clean(value.get("mandatory_condition")),
            unit_price=_clean(value.get("unit_price")),
            total_price=_clean(value.get("total_price")),
            currency=_clean(value.get("currency")),
            source_url=_clean(value.get("source_url")),
            source_row_id=_clean(value.get("source_row_id")),
            source_text=str(value.get("source_text") or "").strip(),
        )


@dataclass(frozen=True)
class GroupTourDay:
    """One supplier-owned day within a multi-day group-tour package."""

    package_day_number: int
    itinerary_day_number: int
    title: str
    description: str = ""
    route: tuple[str, ...] = ()
    highlights: tuple[str, ...] = ()
    included_activities: tuple[str, ...] = ()
    meals: tuple[str, ...] = ()
    overnight_area: str = ""
    accommodation_note: str = ""
    optional_items: tuple[str, ...] = ()
    conditional_items: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()
    source_text: str = ""
    warnings: tuple[str, ...] = ()

    @property
    def as_metadata(self) -> dict[str, Any]:
        return {
            "package_day_number": self.package_day_number,
            "itinerary_day_number": self.itinerary_day_number,
            "title": self.title,
            "description": self.description,
            "route": list(self.route),
            "highlights": list(self.highlights),
            "included_activities": list(self.included_activities),
            "meals": list(self.meals),
            "overnight_area": self.overnight_area,
            "accommodation_note": self.accommodation_note,
            "optional_items": list(self.optional_items),
            "conditional_items": list(self.conditional_items),
            "source_row_ids": list(self.source_row_ids),
            "source_text": self.source_text,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> "GroupTourDay":
        return cls(
            package_day_number=max(0, _int(value.get("package_day_number"))),
            itinerary_day_number=max(0, _int(value.get("itinerary_day_number"))),
            title=_clean(value.get("title")),
            description=str(value.get("description") or "").strip(),
            route=_clean_strings(value.get("route")),
            highlights=_clean_strings(value.get("highlights")),
            included_activities=_clean_strings(value.get("included_activities")),
            meals=_clean_strings(value.get("meals")),
            overnight_area=_clean(value.get("overnight_area")),
            accommodation_note=_clean(value.get("accommodation_note")),
            optional_items=_clean_strings(value.get("optional_items")),
            conditional_items=_clean_strings(value.get("conditional_items")),
            source_row_ids=_clean_strings(value.get("source_row_ids")),
            source_text=str(value.get("source_text") or "").strip(),
            warnings=_clean_strings(value.get("warnings")),
        )


@dataclass(frozen=True)
class GroupTourPackage:
    """Canonical product-level representation of one guided group tour."""

    package_id: str
    title: str
    season: str = "unknown"
    declared_duration_days: int = 0
    duration_days: int = 0
    itinerary_start_day: int = 0
    itinerary_end_day: int = 0
    meeting_point: str = ""
    pickup_time: str = ""
    description: str = ""
    package_inclusions: tuple[str, ...] = ()
    accommodation_policy: GroupTourAccommodationPolicy = field(default_factory=GroupTourAccommodationPolicy)
    transport_policy: tuple[str, ...] = ()
    guide_policy: tuple[str, ...] = ()
    group_style: str = "guided_group"
    commercial_status: str = "included"
    commercial_reason: str = "group_tour_master_product"
    source_url: str = ""
    day_segments: tuple[GroupTourDay, ...] = ()
    commercial_items: tuple[GroupTourCommercialItem, ...] = ()
    source_row_ids: tuple[str, ...] = ()
    source_title: str = ""
    warnings: tuple[str, ...] = ()

    @property
    def canonical_family(self) -> str:
        return GROUP_TOUR_CANONICAL_FAMILY

    @property
    def product_type(self) -> str:
        return GROUP_TOUR_PRODUCT_TYPE

    @property
    def as_metadata(self) -> dict[str, Any]:
        return {
            "kind": GROUP_TOUR_CONTRACT_KIND,
            "schema_version": GROUP_TOUR_CONTRACT_VERSION,
            "canonical_family": self.canonical_family,
            "product_type": self.product_type,
            "package_id": self.package_id,
            "title": self.title,
            "season": self.season,
            "declared_duration_days": self.declared_duration_days,
            "duration_days": self.duration_days,
            "itinerary_start_day": self.itinerary_start_day,
            "itinerary_end_day": self.itinerary_end_day,
            "meeting_point": self.meeting_point,
            "pickup_time": self.pickup_time,
            "description": self.description,
            "package_inclusions": list(self.package_inclusions),
            "accommodation_policy": self.accommodation_policy.as_metadata,
            "transport_policy": list(self.transport_policy),
            "guide_policy": list(self.guide_policy),
            "group_style": self.group_style,
            "commercial_status": self.commercial_status,
            "commercial_reason": self.commercial_reason,
            "source_url": self.source_url,
            "day_segments": [item.as_metadata for item in self.day_segments],
            "commercial_items": [item.as_metadata for item in self.commercial_items],
            "source_row_ids": list(self.source_row_ids),
            "source_title": self.source_title,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> "GroupTourPackage":
        if value.get("kind") != GROUP_TOUR_CONTRACT_KIND:
            raise ValueError("Not a group-tour package domain contract")
        version = _int(value.get("schema_version"))
        if version != GROUP_TOUR_CONTRACT_VERSION:
            raise ValueError(f"Unsupported group-tour contract version: {version}")
        season = _normalize_season(value.get("season"))
        return cls(
            package_id=_clean(value.get("package_id")),
            title=_clean(value.get("title")),
            season=season,
            declared_duration_days=max(0, _int(value.get("declared_duration_days"))),
            duration_days=max(0, _int(value.get("duration_days"))),
            itinerary_start_day=max(0, _int(value.get("itinerary_start_day"))),
            itinerary_end_day=max(0, _int(value.get("itinerary_end_day"))),
            meeting_point=_clean(value.get("meeting_point")),
            pickup_time=_clean(value.get("pickup_time")),
            description=str(value.get("description") or "").strip(),
            package_inclusions=_clean_strings(value.get("package_inclusions")),
            accommodation_policy=GroupTourAccommodationPolicy.from_metadata(value.get("accommodation_policy")),
            transport_policy=_clean_strings(value.get("transport_policy")),
            guide_policy=_clean_strings(value.get("guide_policy")),
            group_style=_clean(value.get("group_style")) or "guided_group",
            commercial_status=_clean(value.get("commercial_status")) or "included",
            commercial_reason=_clean(value.get("commercial_reason")) or "group_tour_master_product",
            source_url=_clean(value.get("source_url")),
            day_segments=tuple(
                GroupTourDay.from_metadata(item)
                for item in value.get("day_segments", ())
                if isinstance(item, Mapping)
            ),
            commercial_items=tuple(
                GroupTourCommercialItem.from_metadata(item)
                for item in value.get("commercial_items", ())
                if isinstance(item, Mapping)
            ),
            source_row_ids=_clean_strings(value.get("source_row_ids")),
            source_title=_clean(value.get("source_title")),
            warnings=_clean_strings(value.get("warnings")),
        )
