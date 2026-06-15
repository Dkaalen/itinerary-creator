"""Canonical multi-day group-tour package contract.

A group tour is one commercial product with several client-facing itinerary
segments.  It is not a collection of independently purchased activities and it
must not be reduced to generic coach transport.  This module owns package
identity, package-day mapping, season, accommodation policy, package-wide
inclusions, optional/commercial add-ons, and source diagnostics.

The contract is deliberately renderer-neutral.  Parsers may attach it to
normalized rows, while preview, editor, inclusion, and PDF consumers can read
it without reinterpreting supplier prose.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

GROUP_TOUR_CONTRACT_KIND = "group_tour_package"
GROUP_TOUR_CONTRACT_VERSION = 1
GROUP_TOUR_PRODUCT_TYPE = "multi_day_group_tour"
GROUP_TOUR_CANONICAL_FAMILY = "guided_group_tour"

_VALID_SEASONS = frozenset({"summer", "winter", "all", "unknown"})
_GROUP_MASTER_MARKERS = (
    "group tour",
    "holiday package",
    "minibus tour",
    "tour around iceland",
    "guided holiday",
)
_CONDITIONAL_MARKERS = (
    "if weather",
    "weather permitting",
    "depending on",
    "not guaranteed",
    "upon request",
    "subject to availability",
    "subject to weather",
    "subject to road",
    "if snow",
    "when conditions",
    "conditions allow",
)

_PACKAGE_DAY_RE = re.compile(r"^\s*Day\s*(\d+)\s*(?::|\s*-\s*)\s*(.*)$", re.IGNORECASE | re.DOTALL)
_ITINERARY_DAY_RE = re.compile(r"\bDay\s*(\d+)\b", re.IGNORECASE)
_DECLARED_DURATION_RE = re.compile(r"\b(\d+)\s*[- ]\s*day\b", re.IGNORECASE)
_TIME_FIELD_RE = re.compile(
    r"\bTime\s*:\s*(.*?)(?=\s+-\s+(?:(?:Meeting\s*point|Includes|Description|Overview|Note)\s*:|[A-ZÁÉÍÓÚÝÞÆÖ])|$)",
    re.IGNORECASE | re.DOTALL,
)
_MEETING_FIELD_RE = re.compile(
    r"\bMeeting\s*point\s*:\s*(.*?)(?=\s+-\s+(?:Time|Includes|Description|Overview|Note)\s*:|$)",
    re.IGNORECASE | re.DOTALL,
)
_INCLUDES_FIELD_RE = re.compile(r"\bIncludes\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Route extraction is intentionally conservative.  These are regions and
# settlements used by the supplied Iceland package corpus, not every attraction
# mentioned in daily prose.
_ICELAND_ROUTE_PLACES = (
    "Reykjavík",
    "Reykjavik",
    "West Iceland",
    "Borgarfjörður",
    "Borgarfjordur",
    "Snæfellsnes",
    "Snaefellsnes",
    "Golden Circle",
    "South Coast",
    "Vík",
    "Vik",
    "Skaftafell",
    "Jökulsárlón",
    "Jokulsarlon",
    "Höfn",
    "Hofn",
    "Vatnajökull",
    "Vatnajokull",
    "Eastfjords",
    "East Fjords",
    "Egilsstaðir",
    "Egilsstadir",
    "Mývatn",
    "Myvatn",
    "Akureyri",
    "Hauganes",
    "Borgarnes",
)

_ICELAND_DAY_ATTRACTIONS = (
    "Hvalfjörður",
    "Hvalfjordur",
    "Hraunfossar",
    "Barnafoss",
    "Deildartunguhver",
    "Reykholt",
    "Snæfellsjökull",
    "Snaefellsjokull",
    "Gerðuberg",
    "Gerduberg",
    "Ytri-Tunga",
    "Ytri Tunga",
    "Arnarstapi",
    "Djúpalónssandur",
    "Djupalonssandur",
    "Kirkjufell",
    "Þingvellir",
    "Thingvellir",
    "Geysir",
    "Strokkur",
    "Gullfoss",
    "Bruarfoss",
    "Seljalandsfoss",
    "Gljúfrabúi",
    "Gljufrabui",
    "Skógafoss",
    "Skogafoss",
    "Reynisfjara",
    "Diamond Beach",
    "VÖK Baths",
    "Vok Baths",
    "Dettifoss",
    "Námskarð",
    "Namaskard",
    "Goðafoss",
    "Godafoss",
)



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


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").replace("\xa0", " ")).strip(" \t\r\n-|:")


def _clean_strings(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return tuple(result)


def _int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _number_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return text
    if number == 0:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def _row_type(row: Mapping[str, Any]) -> str:
    return _clean(row.get("effective_type") or row.get("type"))


def _row_text(row: Mapping[str, Any]) -> str:
    # Prefer the richest structured source.  Concatenating parser ``raw`` text
    # can reintroduce tabular prefixes and duplicate the same prose.
    for key in ("travel_element", "details", "description_raw", "description", "original_title", "title", "raw"):
        text = str(row.get(key) or "").strip()
        if text:
            return text
    return ""


def _group_tour_day_source(row: Mapping[str, Any]) -> str:
    """Return a package-day source beginning with its ``Day N`` label.

    Parsed text rows may keep an embedded city prefix (for example
    ``Reykjavík: Day 1: Golden Circle``), while workbook corpus rows begin
    directly with ``Day 1``.  The contract accepts both forms without
    scanning arbitrary later prose for a day marker.
    """

    for key in ("travel_element", "details", "original_title", "title", "description_raw", "description", "raw"):
        text = str(row.get(key) or "").strip().strip('"')
        if not text:
            continue
        direct = _PACKAGE_DAY_RE.match(text)
        if direct:
            return text
        prefixed = re.match(r"^\s*[^:\n]{1,80}:\s*(Day\s*\d+\s*(?::|\s*-\s*).*)$", text, re.I | re.S)
        if prefixed:
            return prefixed.group(1).strip()
    return _row_text(row)


def _source_row_id(row: Mapping[str, Any], source_name: str = "") -> str:
    row_id = _clean(row.get("row_id"))
    if row_id:
        return row_id
    excel_row = _clean(row.get("excel_row"))
    if excel_row:
        return f"{source_name or 'source'}:{excel_row}"
    digest = hashlib.sha256(_row_text(row).encode("utf-8")).hexdigest()[:12]
    return f"group-tour-{digest}"


def _itinerary_day_number(row: Mapping[str, Any]) -> int:
    match = _ITINERARY_DAY_RE.search(str(row.get("day") or ""))
    return int(match.group(1)) if match else 0


def _package_day_parts(source: str) -> tuple[int, str, str, tuple[str, ...]]:
    match = _PACKAGE_DAY_RE.match(str(source or "").strip())
    if not match:
        return 0, "", str(source or "").strip(), ("group_tour_day_number_missing",)
    day_number = int(match.group(1))
    remainder = match.group(2).strip()
    warnings: list[str] = []

    title = ""
    description = remainder
    lines = [line.strip() for line in remainder.splitlines() if line.strip()]
    if len(lines) >= 2 and len(lines[0].split()) <= 18:
        title = lines[0]
        description = "\n".join(lines[1:])
    else:
        split = re.split(r"\s+-\s+", remainder, maxsplit=1)
        if len(split) == 2 and len(split[0].split()) <= 18:
            title, description = split[0], split[1]
        elif ":" in remainder:
            candidate, rest = remainder.split(":", 1)
            if len(candidate.split()) <= 14 and not re.match(r"^(You|We|After|Today|On|First|Start)\b", candidate, re.I):
                title, description = candidate, rest
    if not title:
        title = f"Group Tour Day {day_number}"
        warnings.append("group_tour_day_title_missing")
    return day_number, polish_title(_clean(title)), str(description or "").strip(), tuple(warnings)


def _master_candidates(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    has_group_rows = any(_row_type(row).casefold() == "group tour" for row in rows)
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, row in enumerate(rows):
        row_type = _row_type(row).casefold()
        source = _row_text(row)
        lower = source.casefold()
        explicit = any(marker in lower for marker in _GROUP_MASTER_MARKERS)
        if row_type == "day overview" and explicit:
            priority = 0
        elif row_type == "activity" and explicit:
            priority = 1
        elif row_type == "activity" and has_group_rows and _DECLARED_DURATION_RE.search(source):
            priority = 2
        else:
            continue
        candidates.append((priority, index, row))
    return [row for _, _, row in sorted(candidates, key=lambda item: (item[0], item[1]))]


def is_group_tour_master_row(row: Mapping[str, Any] | None) -> bool:
    if not row:
        return False
    row_type = _row_type(row).casefold()
    source = _row_text(row).casefold()
    return row_type in {"activity", "day overview"} and any(marker in source for marker in _GROUP_MASTER_MARKERS)


def _day_candidates(rows: Sequence[Mapping[str, Any]], master: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    master_day = _itinerary_day_number(master)
    for index, row in enumerate(rows):
        if row is master:
            continue
        row_type = _row_type(row).casefold()
        source = _group_tour_day_source(row)
        match = _PACKAGE_DAY_RE.match(source.strip())
        if not match:
            continue
        package_day = int(match.group(1))
        itinerary_day = _itinerary_day_number(row)
        if row_type == "group tour":
            priority = 0
        elif row_type == "activity" and itinerary_day >= master_day:
            priority = 1
        else:
            continue
        candidates.append((package_day, priority * 10000 + index, row))

    # Deduplicate package-day rows, preferring explicit Group Tour rows.
    selected: dict[int, tuple[int, Mapping[str, Any]]] = {}
    for package_day, order, row in sorted(candidates, key=lambda item: (item[0], item[1])):
        selected.setdefault(package_day, (order, row))
    return [selected[number][1] for number in sorted(selected)]


def _normalize_season(value: Any) -> str:
    text = _clean(value).casefold()
    if text in _VALID_SEASONS:
        return text
    if "summer" in text:
        return "summer"
    if "winter" in text:
        return "winter"
    if "all" in text or "year round" in text or "year-round" in text:
        return "all"
    return "unknown"


def _infer_season(source: str) -> str:
    lower = str(source or "").casefold()
    has_summer = "summer" in lower or "midnight sun" in lower
    has_winter = "winter" in lower or "ice cave" in lower or "northern lights" in lower
    if has_summer and not has_winter:
        return "summer"
    if has_winter and not has_summer:
        return "winter"
    return "unknown"


def _master_title(source: str, row: Mapping[str, Any]) -> str:
    # ``travel_element`` is the supplier-owned package title in the standard
    # workbook.  Generic activity normalization may otherwise rewrite that
    # row to one of its listed attractions (for example ``Golden Circle Tour``),
    # which would collapse the multi-day product into a single-day activity.
    title = _clean(row.get("travel_element") or row.get("original_title") or row.get("title"))
    if not title:
        title = _clean(source.splitlines()[0] if source else "")
    # Remove city prefix and labelled logistics from source-title variants.
    title = re.split(r"\s+-\s+(?=(?:Meeting\s*point|Time|Includes|Overview)\s*:)", title, maxsplit=1, flags=re.I)[0]
    title = re.sub(r"^\s*(?:Group\s+Tour\s*:\s*)?[^:|]{2,40}:\s*", "", title, count=1, flags=re.I)
    title = re.sub(r"\s*\|\s*", ": ", title)
    return polish_title(_clean(title)) or "Guided Group Tour"


def _field(regex: re.Pattern[str], source: str) -> str:
    match = regex.search(str(source or ""))
    return _clean(match.group(1)) if match else ""


def _package_pickup_time(master: Mapping[str, Any], source: str) -> str:
    explicit = _field(_TIME_FIELD_RE, source) or _clean(master.get("time"))
    if explicit:
        return explicit
    # Legacy supplier overviews often place the departure after a pipe without
    # a Time label.  Treat it as a 30-minute hotel pick-up window, matching the
    # existing client contract while keeping the value package-owned.
    match = re.search(r"\|\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)\b", source)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = match.group(3).replace(".", "").upper()
    end_hour = hour
    end_minute = minute + 30
    if end_minute >= 60:
        end_hour += 1
        end_minute -= 60
    if end_hour > 12:
        end_hour -= 12
    return f"Between {hour}:{minute:02d} {suffix} and {end_hour}:{end_minute:02d} {suffix}"


def _section(source: str, heading: str, stop_headings: Sequence[str]) -> str:
    stop = "|".join(re.escape(item) for item in stop_headings)
    pattern = re.compile(
        rf"(?:^|\n)\s*{re.escape(heading)}\s*\??\s*\n?(.*?)(?=(?:\n\s*(?:{stop})\s*\??\s*(?:\n|:))|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(source)
    return str(match.group(1) or "").strip() if match else ""


def _master_description(source: str) -> str:
    overview = _section(source, "Overview", ("What's included", "What’s included", "Not Included", "What to expect", "Please note"))
    if overview:
        return overview
    prefix = source
    includes = _INCLUDES_FIELD_RE.search(prefix)
    if includes:
        prefix = prefix[: includes.start()]
    prefix = re.sub(r"^.*?(?:Meeting\s*point|Time)\s*:[^\n-]*(?:\s+-\s+)?", "", prefix, count=1, flags=re.I | re.S)
    return polish_client_text(prefix.strip(" -|\n"))


def _master_inclusions(master: Mapping[str, Any], source: str) -> tuple[str, ...]:
    values = master.get("includes") or master.get("source_includes") or ()
    if isinstance(values, str):
        values = [values]
    result = list(_clean_strings(values))

    if not result:
        included_section = _section(source, "What's included", ("Not Included", "What to expect", "Please note"))
        if not included_section:
            included_section = _section(source, "What’s included", ("Not Included", "What to expect", "Please note"))
        if included_section:
            result.extend(_clean_strings(re.split(r"\n+|\s+-\s+", included_section)))
        else:
            raw = _field(_INCLUDES_FIELD_RE, source)
            if raw:
                result.extend(_clean_strings(part for part in raw.split(",")))

    # Some suppliers confirm package activities in the narrative rather than
    # repeating them in the bullet list. Preserve only an explicitly inclusive
    # construction; do not infer ordinary attraction mentions as inclusions.
    for match in re.finditer(
        r"included activities such as\s+(.+?)(?=\s+are (?:arranged|included)|[.!?](?:\s|$))",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        payload = _clean(match.group(1))
        result.extend(
            _clean_strings(
                part
                for part in re.split(r"\s*,\s*|\s+and\s+", payload)
                if _clean(part)
            )
        )
    return _clean_strings(result)


def _day_highlights(package_day: int, inclusions: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for item in inclusions:
        match = re.match(r"\s*Day\s*(\d+)(?:\s*-\s*\d+)?\s*:\s*(.+)", item, flags=re.I)
        if match and int(match.group(1)) == package_day:
            result.append(_clean(match.group(2)))
    return _clean_strings(result)


def _sentences_with_markers(source: str, markers: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for sentence in _SENTENCE_RE.split(str(source or "")):
        clean = _clean(sentence)
        lower = clean.casefold()
        if clean and any(marker in lower for marker in markers):
            result.append(clean)
    return _clean_strings(result)


def _accommodation_note(source: str) -> str:
    candidates: list[str] = []
    for line in str(source or "").splitlines():
        for sentence in _SENTENCE_RE.split(line):
            clean = _clean(sentence)
            lower = clean.casefold()
            if clean and (
                ("night" in lower and any(marker in lower for marker in ("spend", "stay", "spent", "accommodation")))
                or ("accommodation" in lower and any(marker in lower for marker in ("breakfast", "private bathroom", "included in the price")))
            ):
                candidates.append(clean)
    if not candidates:
        return ""
    return min(candidates, key=len)


def _package_day_accommodation_hints(
    source: str,
    inclusions: Sequence[str],
) -> dict[int, str]:
    """Return source-owned overnight wording keyed by package day.

    Supplier package overviews commonly describe accommodation as ranges such
    as ``Day 2-3: West Iceland guesthouse w/breakfast``.  The first number is
    the package day after which that overnight applies.  Preserve the wording
    on the canonical package day instead of creating a synthetic Hotel product.
    """

    hints: dict[int, str] = {}
    candidates = [*str(source or "").replace("–", "-").splitlines(), *inclusions]
    for candidate in candidates:
        clean = _clean(candidate).replace("–", "-")
        match = re.match(r"^Day\s*(\d+)\s*-\s*(\d+)\s*:\s*(.+)$", clean, flags=re.I)
        if not match:
            continue
        wording = _clean(match.group(3))
        if not re.search(r"\b(hotel|guesthouse|accommodation|lodge|resort)\b", wording, flags=re.I):
            continue
        package_day = int(match.group(1))
        hints.setdefault(package_day, polish_client_text(wording))
    return hints


def _apply_package_accommodation_hints(
    day_segments: Sequence[GroupTourDay],
    source: str,
    inclusions: Sequence[str],
) -> tuple[GroupTourDay, ...]:
    hints = _package_day_accommodation_hints(source, inclusions)
    if not hints:
        return tuple(day_segments)

    updated: list[GroupTourDay] = []
    for segment in day_segments:
        hint = hints.get(segment.package_day_number, "")
        if not hint or segment.accommodation_note:
            updated.append(segment)
            continue
        route = list(segment.route)
        overnight_area = _overnight_area(hint, hint, route)
        updated.append(
            replace(
                segment,
                accommodation_note=hint,
                overnight_area=overnight_area,
            )
        )
    return tuple(updated)


def _route_points(source: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for place in _ICELAND_ROUTE_PLACES:
        match = re.search(rf"(?<!\w){re.escape(place)}(?!\w)", source, flags=re.I)
        if match:
            matches.append((match.start(), canonicalize_place_name(place)))
    result: list[str] = []
    seen: set[str] = set()
    for _, place in sorted(matches):
        key = place.casefold()
        if key not in seen:
            seen.add(key)
            result.append(place)
    return tuple(result)


def _source_attractions(source: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for place in _ICELAND_DAY_ATTRACTIONS:
        match = re.search(rf"(?<!\w){re.escape(place)}(?!\w)", source, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), canonicalize_place_name(place)))
    result: list[str] = []
    seen: set[str] = set()
    for _, place in sorted(matches):
        key = place.casefold()
        if key not in seen:
            seen.add(key)
            result.append(place)
    return tuple(result)


def _overnight_area(source: str, accommodation_note: str, route: Sequence[str]) -> str:
    del source, route  # The overnight place must be present in the accommodation sentence itself.
    note_route = _route_points(accommodation_note)
    return note_route[-1] if note_route else ""


def _meal_markers(source: str, highlights: Sequence[str]) -> tuple[str, ...]:
    text = f"{source}\n{' '.join(highlights)}".casefold()
    result: list[str] = []
    if "breakfast" in text:
        result.append("Breakfast")
    if "lunch" in text and not re.search(r"lunch\s+(?:available|for purchase|not included)", text):
        result.append("Lunch")
    if "dinner" in text and not re.search(r"dinner\s+(?:available|for purchase|not included)", text):
        result.append("Dinner")
    return tuple(result)


def _build_day(row: Mapping[str, Any], inclusions: Sequence[str], source_name: str) -> GroupTourDay:
    source = _group_tour_day_source(row)
    package_day, title, description, warnings = _package_day_parts(source)
    # Legacy parser rows may hold a cleaner, more complete supplier heading in
    # ``title`` while ``details`` has already been compacted.  Prefer that
    # explicit short heading, but never treat a full ``Day N: ...`` source row
    # from the workbook corpus as a title.
    explicit_title = re.sub(r"\s+Today$", "", _clean(row.get("title")), flags=re.IGNORECASE)
    source_title_tokens = {
        token.casefold()
        for token in re.findall(r"[\wÀ-ÖØ-öø-ÿÞþÆæ]+", title)
        if len(token) > 2
    }
    explicit_title_tokens = {
        token.casefold()
        for token in re.findall(r"[\wÀ-ÖØ-öø-ÿÞþÆæ]+", explicit_title)
        if len(token) > 2
    }
    if (
        explicit_title
        and not re.match(r"^Day\s*\d+\b", explicit_title, flags=re.IGNORECASE)
        and len(explicit_title.split()) <= 20
        and explicit_title.casefold() not in {"activity", "group tour"}
        and source_title_tokens.issubset(explicit_title_tokens)
    ):
        title = polish_title(explicit_title)
    itinerary_day = _itinerary_day_number(row)
    package_highlights = _day_highlights(package_day, inclusions)
    source_attractions = _source_attractions(source)
    highlights = source_attractions or package_highlights
    accommodation_note = _accommodation_note(source)
    route = list(_route_points(source))
    source_city = canonicalize_place_name(_clean(row.get("city")))
    if (
        source_city
        and source_city.casefold() not in {"iceland", "group tour"}
        and not re.fullmatch(r"day\s*\d+", source_city, flags=re.IGNORECASE)
        and source_city.casefold() not in {place.casefold() for place in route}
    ):
        route.append(source_city)
    optional_items = _sentences_with_markers(source, ("optional", "can be added", "extra is"))
    conditional_items = _sentences_with_markers(source, _CONDITIONAL_MARKERS)
    included_activities = _clean_strings(
        item
        for item in highlights
        if not re.search(
            r"\b(hotel|guesthouse|accommodation|arrival|pick[-‑ ]?up|minibus)\b",
            item,
            re.I,
        )
    )
    return GroupTourDay(
        package_day_number=package_day,
        itinerary_day_number=itinerary_day,
        title=title,
        description=description,
        route=tuple(route),
        highlights=highlights,
        included_activities=included_activities,
        meals=_meal_markers(source, highlights),
        overnight_area=_overnight_area(source, accommodation_note, route),
        accommodation_note=accommodation_note,
        optional_items=optional_items,
        conditional_items=conditional_items,
        source_row_ids=(_source_row_id(row, source_name),),
        source_text=source,
        warnings=warnings,
    )


def _accommodation_policy(
    source: str,
    inclusions: Sequence[str],
    duration_days: int,
    day_segments: Sequence[GroupTourDay],
) -> GroupTourAccommodationPolicy:
    wording = _clean_strings(
        item
        for item in inclusions
        if re.search(r"\b(hotel|guesthouse|accommodation|private bathroom|breakfast)\b", item, re.I)
    )
    day_notes = _clean_strings(day.accommodation_note for day in day_segments if day.accommodation_note)
    combined = "\n".join((source, *wording, *day_notes))
    lower = combined.casefold()
    included = bool(
        re.search(r"\b(hotel|guesthouse|accommodation|hotel stays?)\b", lower)
        and not re.search(r"\b(accommodation|hotel)\s+not\s+included\b", lower)
    )
    explicit_nights = re.search(r"\b(\d+)\s+nights?\b", combined, flags=re.I)
    nights = int(explicit_nights.group(1)) if explicit_nights else (max(0, duration_days - 1) if included else 0)
    nights_inferred = bool(included and nights and not explicit_nights)
    room_basis = ""
    if "sharing room basis" in lower or "shared room basis" in lower:
        room_basis = "Sharing room basis"
    elif "double room" in lower:
        room_basis = "Double room"
    elif "standard room" in lower:
        room_basis = "Standard room"
    bathroom = "Private bathroom" if "private bathroom" in lower else ""
    meal_plan = "Breakfast included" if "breakfast" in lower else ""
    exact_properties_confirmed = bool(
        included
        and re.search(r"\b(?:hotel|guesthouse)\s+[A-ZÁÉÍÓÚÝÞÆÖ]", combined)
        and not re.search(r"\b(or similar|subject to availability|countryside hotel|hotel stays?)\b", combined, re.I)
    )
    warnings: list[str] = []
    if nights_inferred:
        warnings.append("accommodation_nights_inferred_from_package_duration")
    if included and not wording and not day_notes:
        warnings.append("accommodation_policy_lacks_source_wording")
    return GroupTourAccommodationPolicy(
        included=included,
        nights=nights,
        nights_inferred=nights_inferred,
        room_basis=room_basis,
        bathroom=bathroom,
        meal_plan=meal_plan,
        exact_properties_confirmed=exact_properties_confirmed,
        source_wording=_clean_strings((*wording, *day_notes)),
        warnings=tuple(warnings),
    )


def _policies(inclusions: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    transport = _clean_strings(
        item
        for item in inclusions
        if re.search(r"\b(pick[- ]?up|drop[- ]?off|transport|transfer|minibus|vehicle|coach|wifi)\b", item, re.I)
    )
    guide = _clean_strings(item for item in inclusions if re.search(r"\bguide|guidance\b", item, re.I))
    return transport, guide


def _group_style(source: str) -> str:
    lower = source.casefold()
    if "small-group" in lower or "small group" in lower:
        return "guided_small_group"
    if "minibus" in lower:
        return "guided_minibus"
    return "guided_group"


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


def _package_id(title: str, source_name: str, master: Mapping[str, Any], day_rows: Sequence[Mapping[str, Any]]) -> str:
    payload = "|".join(
        (
            source_name,
            title,
            _source_row_id(master, source_name),
            *(_source_row_id(row, source_name) for row in day_rows),
        )
    )
    return f"group-tour-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def build_group_tour_package(
    rows: Iterable[Mapping[str, Any]],
    *,
    season: str = "",
    source_name: str = "",
    package_id: str = "",
) -> GroupTourPackage | None:
    """Build one canonical package from source-owned rows.

    Known facts are preserved.  Missing facts remain empty or receive an
    explicit warning; conflicting season/duration/day mappings are never
    silently repaired.
    """

    row_list = list(rows or ())
    masters = _master_candidates(row_list)
    if not masters:
        return None
    master = masters[0]
    master_source = _row_text(master)
    day_rows = _day_candidates(row_list, master)
    if not day_rows:
        return None

    title = _master_title(master_source, master)
    inclusions = _master_inclusions(master, master_source)
    day_segments = tuple(_build_day(row, inclusions, source_name) for row in day_rows)
    day_segments = _apply_package_accommodation_hints(day_segments, master_source, inclusions)
    declared_match = _DECLARED_DURATION_RE.search(title or master_source)
    declared_duration = int(declared_match.group(1)) if declared_match else 0
    observed_duration = len(day_segments)
    highest_package_day = max((day.package_day_number for day in day_segments), default=0)
    # Product duration is a package fact, not merely the number of day rows that
    # happened to be supplied.  This also prevents output such as "Day 6 of 4"
    # when a partial supplier export retains the declared six-day programme.
    duration = max(observed_duration, highest_package_day, declared_duration)
    itinerary_days = tuple(day.itinerary_day_number for day in day_segments if day.itinerary_day_number)
    itinerary_start = min(itinerary_days) if itinerary_days else _itinerary_day_number(master)
    itinerary_end = max(itinerary_days) if itinerary_days else itinerary_start + max(0, duration - 1)

    warnings: list[str] = []
    if len(masters) > 1:
        warnings.append("multiple_group_tour_master_rows")
    package_days = [day.package_day_number for day in day_segments]
    expected_days = list(range(1, duration + 1))
    if package_days != expected_days:
        warnings.append("group_tour_package_day_sequence_mismatch")
    if itinerary_days and itinerary_days != tuple(range(itinerary_start, itinerary_start + duration)):
        warnings.append("group_tour_itinerary_day_sequence_mismatch")
    if declared_duration and declared_duration != observed_duration:
        warnings.append("group_tour_declared_duration_conflict")

    explicit_season = _normalize_season(season)
    inferred_season = _infer_season(f"{title}\n{master_source}")
    if explicit_season != "unknown":
        package_season = explicit_season
        if inferred_season != "unknown" and inferred_season != explicit_season:
            warnings.append("group_tour_season_source_conflict")
    else:
        package_season = inferred_season

    status, reason = _commercial_status(master, day_rows)
    accommodation = _accommodation_policy(master_source, inclusions, duration, day_segments)
    transport_policy, guide_policy = _policies(inclusions)
    commercial_items = tuple(
        item
        for item in (_commercial_item(row, source_name) for row in row_list)
        if item is not None
    )
    source_ids = _clean_strings(
        (_source_row_id(master, source_name),)
        + tuple(_source_row_id(row, source_name) for row in day_rows)
    )
    source_url = _clean(master.get("url"))
    if not source_url:
        match = _URL_RE.search(master_source)
        source_url = match.group(0) if match else ""

    return GroupTourPackage(
        package_id=package_id or _package_id(title, source_name, master, day_rows),
        title=title,
        season=package_season,
        declared_duration_days=declared_duration,
        duration_days=duration,
        itinerary_start_day=itinerary_start,
        itinerary_end_day=itinerary_end,
        meeting_point=_field(_MEETING_FIELD_RE, master_source) or _clean(master.get("meeting_point")),
        pickup_time=_package_pickup_time(master, master_source),
        description=_master_description(master_source),
        package_inclusions=inclusions,
        accommodation_policy=accommodation,
        transport_policy=transport_policy,
        guide_policy=guide_policy,
        group_style=_group_style(f"{title}\n{master_source}"),
        commercial_status=status,
        commercial_reason=reason,
        source_url=source_url,
        day_segments=day_segments,
        commercial_items=commercial_items,
        source_row_ids=source_ids,
        source_title=_clean(master.get("original_title") or master.get("travel_element") or master.get("title")),
        warnings=_clean_strings(warnings),
    )


def annotate_group_tour_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    season: str = "",
    source_name: str = "",
) -> list[dict[str, Any]]:
    """Attach the package contract and day references without changing output.

    The package metadata is attached only to the master row.  Daily rows receive
    the matching day-segment metadata and package ID.  Independent pre/post
    hotels and commercial add-ons remain separate rows.
    """

    updated = [deepcopy(dict(row)) for row in rows or ()]
    package = build_group_tour_package(updated, season=season, source_name=source_name)
    if package is None:
        return updated

    masters = _master_candidates(updated)
    day_rows = _day_candidates(updated, masters[0]) if masters else []
    if masters:
        master = masters[0]
        master["group_tour_package"] = package.as_metadata
        master["group_tour_package_id"] = package.package_id
    segments = {day.package_day_number: day for day in package.day_segments}
    for row in day_rows:
        package_day, _, _, _ = _package_day_parts(_group_tour_day_source(row))
        segment = segments.get(package_day)
        if segment is None:
            continue
        row["group_tour_package_id"] = package.package_id
        row["group_tour_day"] = segment.as_metadata
    return updated


def group_tour_package_from_row(row: Mapping[str, Any] | None) -> GroupTourPackage | None:
    if not row:
        return None
    value = row.get("group_tour_package")
    if not isinstance(value, Mapping):
        return None
    try:
        return GroupTourPackage.from_metadata(value)
    except (TypeError, ValueError):
        return None


def group_tour_day_from_row(row: Mapping[str, Any] | None) -> GroupTourDay | None:
    if not row:
        return None
    value = row.get("group_tour_day")
    if not isinstance(value, Mapping):
        return None
    try:
        return GroupTourDay.from_metadata(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "GROUP_TOUR_CANONICAL_FAMILY",
    "GROUP_TOUR_CONTRACT_KIND",
    "GROUP_TOUR_CONTRACT_VERSION",
    "GROUP_TOUR_PRODUCT_TYPE",
    "GroupTourAccommodationPolicy",
    "GroupTourCommercialItem",
    "GroupTourDay",
    "GroupTourPackage",
    "annotate_group_tour_rows",
    "build_group_tour_package",
    "group_tour_day_from_row",
    "group_tour_package_from_row",
    "is_group_tour_master_row",
]
