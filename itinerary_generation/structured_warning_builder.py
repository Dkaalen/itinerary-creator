"""Structured-document warning helpers."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.product_rules import product_warning
from itinerary_generation.structured_model import ModelWarning
from itinerary_generation.structured_row_helpers import _has_structured_activity_supplier_text, _row_id

_ACTIVITY_SIGNAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("fjord", "fjords", "fjorden", "fjordsafari", "fjord safari"),
    ("cruise", "boat", "sailing", "ferry"),
    # Generic words like "ticket" or "admission" are not specific enough to
    # imply a museum/gallery product. Keeping this signal narrow avoids false
    # warnings for rows such as generic cable-car round-trip tickets.
    ("museum", "gallery"),
    ("walking", "walk", "guided walk", "city center", "city centre"),
    ("northern lights", "aurora", "auroras"),
    ("husky", "reindeer", "safari"),
    ("cable car", "fjellheisen", "funicular", "funicual"),
    ("munch", "munch museum"),
)

_STOP_TOKENS = {
    "activity", "experience", "tour", "guided", "ticket", "tickets", "included",
    "with", "from", "into", "your", "the", "and", "for", "day", "time",
    "tromso", "tromsø", "oslo", "bergen", "helsinki", "rovaniemi", "tallinn",
}


def _signature_tokens(value: str) -> set[str]:
    tokens = {token.lower() for token in re.findall(r"[A-Za-zÀ-ÿøØåÅäÄöÖæÆðÐþÞ]{4,}", value or "")}
    return {token for token in tokens if token not in _STOP_TOKENS}


def _source_signal_warnings(title: str, source: str, row_id: str) -> list[ModelWarning]:
    """Return warnings when a cleaned activity title loses source-specific signals.

    This is a diagnostic guardrail, not a hard blocker.  It catches the class of
    bugs where one activity title/detail is accidentally overwritten by another
    row later in the pipeline, such as a museum title replacing a fjord cruise.
    """

    title_lower = title.lower()
    source_lower = source.lower()
    if not title_lower or not source_lower:
        return []

    warnings: list[ModelWarning] = []
    source_tokens = _signature_tokens(source_lower)
    title_tokens = _signature_tokens(title_lower)
    # If both sides have meaningful tokens but none overlap, the title may be
    # an inference or a cross-row contamination. Do not warn on very thin source
    # rows because those often only contain time/booking metadata.
    if len(source_tokens) >= 2 and len(title_tokens) >= 2 and source_tokens.isdisjoint(title_tokens):
        warnings.append(ModelWarning(
            code="activity_title_not_supported_by_source",
            message="Activity title has little overlap with its source row; review for possible cross-row title contamination.",
            source_row_ids=(row_id,),
        ))

    for signal_group in _ACTIVITY_SIGNAL_GROUPS:
        source_has_signal = any(signal in source_lower for signal in signal_group)
        title_has_signal = any(signal in title_lower for signal in signal_group)
        if source_has_signal and not title_has_signal:
            signal_label = signal_group[0].replace("_", " ")
            warnings.append(ModelWarning(
                code="activity_source_signal_missing_from_title",
                message=f"Activity source row mentions {signal_label}, but the display title does not; review before final output.",
                source_row_ids=(row_id,),
            ))
            break

    return warnings


def _ambiguous_row_warnings(row: dict) -> tuple[ModelWarning, ...]:
    """Flag rows where the model should not over-trust an inferred title."""

    row_type = str(get_row_type(row) or "")
    if row.get("group_tour_role") in {"package_master", "day_segment"} or row_type != "Activity":
        return ()

    # Use only supplier/source fields for ambiguity checks. The normalized
    # title may already contain an inferred product name, which would otherwise
    # make the inference look falsely explicit.
    source = "\n".join(
        str(row.get(key, "") or "")
        for key in ("raw", "original_title", "details")
        if str(row.get(key, "") or "").strip()
    )
    source_lower = source.lower()
    title = str(row.get("title", "") or "")
    title_lower = title.lower()
    row_id = _row_id(row)

    warnings: list[ModelWarning] = []
    warning_code, warning_message = product_warning(row, source)
    if warning_code:
        warnings.append(ModelWarning(
            code=warning_code,
            message=warning_message,
            source_row_ids=(row_id,),
        ))

    warnings.extend(_source_signal_warnings(title, source, row_id))

    return tuple(dict.fromkeys(warnings))




def _row_data_warnings(row: dict) -> tuple[ModelWarning, ...]:
    """Return source-data warnings that should survive into the document model."""

    row_id = _row_id(row)
    row_type = str(get_row_type(row) or "")
    source = " ".join(
        str(row.get(key, "") or "")
        for key in ("raw", "original_title", "details", "title")
        if str(row.get(key, "") or "").strip()
    )
    source_lower = source.lower()
    warnings: list[ModelWarning] = []

    if row.get("group_tour_role") in {"package_master", "day_segment"}:
        return ()

    if row_type == "Activity":
        time_text = str(row.get("time") or "")
        suspicious_am = re.search(r"\b(?:1|2|3|4|5):\d{2}\s*AM\b", time_text, flags=re.IGNORECASE)
        is_normal_night_activity = any(marker in source_lower for marker in [
            "northern light", "aurora", "overnight", "night train", "night cruise", "dinner cruise",
        ])
        is_daytime_product = any(marker in source_lower for marker in [
            "sightseeing", "walking tour", "city tour", "fjord cruise", "canal tour", "hop-on", "hop on",
        ])
        if suspicious_am and is_daytime_product and not is_normal_night_activity:
            warnings.append(ModelWarning(
                code="suspicious_activity_time",
                message=f"Activity time {time_text} looks unusual for a daytime sightseeing product; verify AM/PM before final output.",
                source_row_ids=(row_id,),
            ))
        product = row.get("activity_product") if isinstance(row.get("activity_product"), dict) else {}
        if not product and _has_structured_activity_supplier_text(source_lower):
            warnings.append(ModelWarning(
                code="low_confidence_activity_structure",
                message=(
                    "Structured supplier activity text did not match a known product fingerprint; "
                    "review the title, meeting point and inclusions before final output."
                ),
                source_row_ids=(row_id,),
            ))

    if row_type == "Hotel":
        hotel_name = str(row.get("hotel_name") or "").strip()
        generic_hotel_name = bool(re.fullmatch(r"(?:\d\s*[- ]?star\s+)?hotel(?:\s+in\s+.+)?", hotel_name, flags=re.IGNORECASE))
        if not hotel_name or generic_hotel_name:
            warnings.append(ModelWarning(
                code="missing_hotel_name",
                message="Accommodation row has no hotel name; verify supplier data before final output.",
                source_row_ids=(row_id,),
            ))

    return tuple(dict.fromkeys(warnings))

__all__ = [
    "_ACTIVITY_SIGNAL_GROUPS",
    "_STOP_TOKENS",
    "_has_structured_activity_supplier_text",
    "_signature_tokens",
    "_source_signal_warnings",
    "_ambiguous_row_warnings",
    "_row_data_warnings",
]
