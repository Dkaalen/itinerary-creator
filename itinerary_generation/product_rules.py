"""Central product rule registry for client-facing itinerary content.

The registry owns high-risk product identity decisions that used to be scattered
across title, description and validation helpers.  A match can be strong
(explicitly supported by the supplier/source row) or weak (possible inference
that must use a safe generic title and carry a warning).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Iterable, Literal

from itinerary_generation.activity_cache import freeze_activity_row, freeze_activity_values, thaw_activity_row, thaw_activity_values
from itinerary_generation.tallinn import is_tallinn_ferry_framework, is_tallinn_old_town_guided_tour
from itinerary_generation.title_routes import _looks_like_norway_in_a_nutshell, _route_label_from_activity_text
from itinerary_generation.activity_products import fingerprint_activity
from itinerary_generation.fjordtours_activity_catalogue import fjordtours_activity_description

ProductConfidence = Literal["strong", "weak"]


@dataclass(frozen=True)
class ProductRule:
    """Declarative metadata for one special product rule."""

    rule_id: str
    label: str
    strong_title: str = ""
    weak_title: str = ""
    warning_code: str = ""
    warning_message: str = ""


@dataclass(frozen=True)
class ProductRuleMatch:
    """Result returned by the product registry."""

    rule_id: str
    title: str = ""
    confidence: ProductConfidence = "strong"
    description: str = ""
    warning_code: str = ""
    warning_message: str = ""

    @property
    def is_strong(self) -> bool:
        return self.confidence == "strong"

    @property
    def is_weak(self) -> bool:
        return self.confidence == "weak"


PRODUCT_RULES: tuple[ProductRule, ...] = (
    ProductRule("tallinn_old_town_guided_tour", "Tallinn Old Town guided tour", strong_title="Old Town Guided Tour"),
    ProductRule("tallinn_ferry_framework", "Helsinki–Tallinn ferry framework", strong_title="Day Excursion to Tallinn"),
    ProductRule("norway_in_a_nutshell", "Norway in a Nutshell", strong_title="Norway in a Nutshell"),
    ProductRule("munch_museum", "Munch Museum", strong_title="Munch Museum Visit"),
    ProductRule("fjellheisen", "Fjellheisen Cable Car", strong_title="Fjellheisen Cable Car"),
    ProductRule(
        "tromso_viewpoint_ticket_possible_fjellheisen",
        "Possible Tromsø viewpoint ticket",
        weak_title="Round-trip viewpoint ticket in Tromsø",
        warning_code="ambiguous_activity_title",
        warning_message=(
            "Activity title came from a generic 'Round Trip Ticket' row in Tromsø; "
            "confirm the exact product name before final output."
        ),
    ),
    ProductRule("santa_claus_friends", "Santa Claus and friends", strong_title="Meet Santa Claus and his friends"),
    ProductRule("korouoma_canyon", "Korouoma Canyon"),
)

_RULE_BY_ID = {rule.rule_id: rule for rule in PRODUCT_RULES}


def product_context(row: dict | None = None, *values: object) -> str:
    """Return normalized source text used for product decisions."""

    pieces: list[str] = []
    if row:
        for key in ("raw", "display_title", "title", "original_title", "details", "description", "city"):
            value = row.get(key, "")
            if value:
                pieces.append(str(value))
        for key in ("includes", "notable_sights"):
            value = row.get(key, [])
            if isinstance(value, (list, tuple, set)):
                pieces.extend(str(item) for item in value if item)
            elif value:
                pieces.append(str(value))
    pieces.extend(str(value) for value in values if value)
    return " ".join(pieces)


def product_context_lower(row: dict | None = None, *values: object) -> str:
    return product_context(row, *values).lower()


def product_source_context(row: dict | None = None, *values: object) -> str:
    """Return supplier/source text only, avoiding inferred normalized titles."""

    pieces: list[str] = []
    if row:
        for key in ("raw", "original_title", "details", "description", "city"):
            value = row.get(key, "")
            if value:
                pieces.append(str(value))
        for key in ("includes", "notable_sights"):
            value = row.get(key, [])
            if isinstance(value, (list, tuple, set)):
                pieces.extend(str(item) for item in value if item)
            elif value:
                pieces.append(str(value))
        if not any(str(piece).strip() for piece in pieces):
            fallback_title = row.get("title", "")
            if fallback_title:
                pieces.append(str(fallback_title))
    if not pieces:
        pieces.extend(str(value) for value in values if value)
    return " ".join(pieces)


def product_source_context_lower(row: dict | None = None, *values: object) -> str:
    return product_source_context(row, *values).lower()


def _match(rule_id: str, *, title: str | None = None, confidence: ProductConfidence = "strong", description: str = "") -> ProductRuleMatch:
    rule = _RULE_BY_ID[rule_id]
    chosen_title = title if title is not None else (rule.strong_title if confidence == "strong" else rule.weak_title)
    return ProductRuleMatch(
        rule_id=rule.rule_id,
        title=chosen_title,
        confidence=confidence,
        description=description or product_description(rule.rule_id, confidence=confidence),
        warning_code=rule.warning_code if confidence == "weak" else "",
        warning_message=rule.warning_message if confidence == "weak" else "",
    )


def _titleish_source_context(row: dict | None = None, *values: object) -> str:
    """Return only high-confidence title/heading text for product identity.

    Long supplier descriptions can mention nearby sights such as museums in
    route notes. Those incidental mentions must not rename the actual product.
    """

    pieces: list[str] = []
    if row:
        for key in ("display_title", "title", "original_title"):
            value = row.get(key, "")
            if value:
                pieces.append(str(value))
        details = str(row.get("details", "") or "")
        if details:
            first_line = next((line.strip() for line in details.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()), "")
            first_segment = first_line.split("|", 1)[0].strip()
            if first_segment:
                pieces.append(first_segment)
    if values:
        # Extra values passed to product matching are often the candidate title
        # followed by long source text. Only the first supplied value is safe to
        # treat as title-like evidence.
        first = str(values[0] or "").strip()
        if first:
            pieces.append(first.split("|", 1)[0].strip())
    return " ".join(piece for piece in pieces if piece).strip()


def has_explicit_munch_museum_evidence(row: dict | None = None, *values: object) -> bool:
    """Return True only when the row itself is a Munch Museum product.

    Oslofjord cruise descriptions may mention that the boat passes near the
    Munch Museum. That is incidental sightseeing context and must not override
    the supplier's cruise title.
    """

    titleish = _titleish_source_context(row, *values).lower()
    if "munch" in titleish and "museum" in titleish:
        return True
    source = product_source_context_lower(row, *values)
    if not ("munch" in source and "museum" in source):
        return False
    explicit_product = re.search(
        r"(?:munch\s+museum[^.\n]{0,80}\b(?:ticket|tickets|admission|entry|visit)\b|\b(?:ticket|tickets|admission|entry|visit)\b[^.\n]{0,80}munch\s+museum)",
        source,
        flags=re.IGNORECASE,
    )
    incidental_context = re.search(r"(?:pass(?:ing)?|near|near to|close to|coastline|view of|stop at)\b[^.\n]{0,120}munch\s+museum", source, flags=re.IGNORECASE)
    return bool(explicit_product and not incidental_context)


def has_explicit_fjellheisen_evidence(row: dict | None = None, *values: object) -> bool:
    """Return True only when supplier/source text supports Fjellheisen naming.

    Normalized titles may already contain an inferred product name, so they are
    deliberately ignored when raw/original/detail text exists.
    """

    lower = product_source_context_lower(row, *values)
    if "fjellheisen" in lower:
        return True
    if "trom" not in lower:
        return False
    return any(marker in lower for marker in ("cable car", "gondola", "mountain lift", "mountain cable", "aerial tramway"))


def is_weak_tromso_viewpoint_ticket(row: dict | None = None, *values: object) -> bool:
    """Return True for possible-but-not-proven Tromsø viewpoint tickets."""

    lower = product_source_context_lower(row, *values)
    return "round trip ticket" in lower and "trom" in lower and not has_explicit_fjellheisen_evidence(row, *values)


@lru_cache(maxsize=4096)
def _find_product_match_cached(
    row_snapshot: tuple[tuple[str, object], ...],
    values_snapshot: tuple[object, ...],
) -> ProductRuleMatch | None:
    row = thaw_activity_row(row_snapshot)
    values = thaw_activity_values(values_snapshot)
    lower = product_context_lower(row, *values)
    if not lower.strip():
        return None

    if row and is_tallinn_old_town_guided_tour(row, *values):
        return _match("tallinn_old_town_guided_tour")
    if row and is_tallinn_ferry_framework(row, *values):
        return _match("tallinn_ferry_framework")

    # Keep legacy registry decisions before the broader activity-fingerprint
    # catalogue.  The catalogue is useful for normalized activity metadata, but
    # these rules intentionally distinguish explicit/weak source evidence and
    # own specific warning behavior.
    if has_explicit_munch_museum_evidence(row, *values):
        return _match("munch_museum")

    if has_explicit_fjellheisen_evidence(row, *values):
        return _match("fjellheisen")
    if is_weak_tromso_viewpoint_ticket(row, *values):
        return _match("tromso_viewpoint_ticket_possible_fjellheisen", confidence="weak")

    product = fingerprint_activity(row, *values)
    if product and product.display_title:
        return ProductRuleMatch(
            rule_id=product.canonical_family,
            title=product.display_title,
            confidence=product.confidence,
            description=product_description(product.canonical_family, confidence=product.confidence),
            warning_code="ambiguous_activity_title" if product.confidence == "weak" else "",
            warning_message="Activity product was inferred from weak source evidence; confirm the exact product name before final output." if product.confidence == "weak" else "",
        )

    if _looks_like_norway_in_a_nutshell(lower):
        return _match("norway_in_a_nutshell", title=_route_label_from_activity_text(product_context(row, *values)))

    if "santa claus" in lower and "friends" in lower:
        return _match("santa_claus_friends")

    if "korouoma" in lower:
        return _match("korouoma_canyon", title="")

    return None


def find_product_match(row: dict | None = None, *values: object) -> ProductRuleMatch | None:
    """Return the highest-confidence product match, cached by source content."""

    return _find_product_match_cached(freeze_activity_row(row), freeze_activity_values(values))


def clear_product_rule_cache() -> None:
    _find_product_match_cached.cache_clear()


def product_rule_cache_info():
    return _find_product_match_cached.cache_info()


def product_description(rule_id: str, *, confidence: ProductConfidence = "strong") -> str:
    """Return the registry-owned fallback description for a product rule."""

    if rule_id == "tallinn_old_town_guided_tour":
        return "Explore Tallinn’s Old Town with a guide during your time ashore, with key landmarks and local context introduced along the walking route."
    if rule_id == "tallinn_ferry_framework":
        return "Travel between Helsinki and Tallinn by ferry, with the crossings forming the logistics for your time in Tallinn."
    if rule_id == "munch_museum":
        return "Visit the Munch Museum at your own pace, with pre-arranged admission giving you time to explore the galleries and exhibitions independently."
    if rule_id == "fjellheisen":
        return "Use your round-trip Fjellheisen ticket for a flexible visit above Tromsø, with time to enjoy the panoramic views over the city, fjords and surrounding mountains."
    if rule_id == "tromso_viewpoint_ticket_possible_fjellheisen":
        return "Use your pre-arranged ticket for a flexible viewpoint visit in Tromsø, with time to enjoy the surrounding views during the day."
    if rule_id == "santa_claus_friends":
        return "Experience a festive family-friendly visit with Santa Claus, reindeer and elves, including seasonal activities, warm refreshments and time for a private Santa meeting where included."
    if rule_id == "korouoma_canyon":
        return "Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience."
    fjordtours_description = fjordtours_activity_description(rule_id)
    if fjordtours_description:
        return fjordtours_description
    return ""


def product_warning(row: dict | None = None, *values: object) -> tuple[str, str]:
    """Return ``(code, message)`` for weak product matches, otherwise empty."""

    match = find_product_match(row, *values)
    if match and match.is_weak:
        return match.warning_code, match.warning_message
    return "", ""
