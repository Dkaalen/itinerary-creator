"""Integrity checks for the structured itinerary document.

These checks are deliberately model-level rather than renderer-level. They make
broken object identity, item/day drift and accidental row merging visible before
HTML/PDF rendering can hide the problem.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from itinerary_generation.structured_model import ItineraryDocument, ModelWarning, SourceRowRef, StructuredListItem
from shared.commercial_markers import has_self_transfer_marker

_REVIEW_KIND_COVERAGE = {"activity", "accommodation"}
_INCLUDED_STATUSES = {"", "included"}
_STOP_TOKENS = {
    "activity", "admission", "arranged", "centre", "center", "city", "cruise", "day",
    "duration", "evening", "experience", "from", "guided", "hotel", "included", "includes",
    "into", "morning", "night", "only", "private", "self", "the", "ticket", "tickets",
    "time", "tour", "transfer", "walk", "walking", "with", "your",
    "bergen", "helsinki", "ivalo", "kakslauttenen", "oslo", "rovaniemi", "tallinn",
    "tromso", "tromsø",
}
_SOURCE_SIGNAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("fjord", "fjords", "fjorden", "fjord safari", "fjordsafari"),
    ("cruise", "boat", "sailing", "ferry"),
    ("museum", "gallery", "munch"),
    ("walking", "walk", "city center", "city centre"),
    ("northern lights", "aurora", "auroras"),
    ("husky", "reindeer", "safari"),
    ("cable car", "fjellheisen", "funicular", "funicual"),
)


def _status_is_included(value: str) -> bool:
    return str(value or "included").strip().lower() in _INCLUDED_STATUSES


def _compact_tokens(value: str) -> set[str]:
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-zÀ-ÿøØåÅäÄöÖæÆðÐþÞ]{4,}", str(value or ""))
    }
    return {token for token in tokens if token not in _STOP_TOKENS}


def _source_text(source: SourceRowRef | None) -> str:
    if source is None:
        return ""
    # Use supplier/source text, not the normalized display title. The normalized
    # title may already contain an inferred product name, which would make weak
    # source support look falsely safe. ``SourceRowRef.raw_text`` can fall back
    # to the normalized title when no raw/details field exists, so ignore that
    # fallback when an original supplier title is available.
    raw_text = str(source.raw_text or "").strip()
    normalized_title = str(source.title or "").strip()
    original_title = str(source.original_title or "").strip()
    if original_title and raw_text == normalized_title:
        raw_text = ""
    return "\n".join(
        value
        for value in (
            original_title,
            raw_text,
            source.city,
        )
        if str(value or "").strip()
    )


def _item_identity_text(item) -> str:
    return "\n".join(
        value
        for value in (
            item.title,
            "\n".join(item.detail_lines or ()),
            item.destination,
        )
        if str(value or "").strip()
    )


def _inclusion_items_by_source_id(document: ItineraryDocument) -> dict[str, list[StructuredListItem]]:
    mapping: dict[str, list[StructuredListItem]] = defaultdict(list)
    for section in document.inclusions:
        for list_item in section.items:
            for row_id in list_item.source_row_ids:
                if row_id:
                    mapping[row_id].append(list_item)
    return mapping


def _exclusion_items_by_source_id(document: ItineraryDocument) -> dict[str, list[StructuredListItem]]:
    mapping: dict[str, list[StructuredListItem]] = defaultdict(list)
    for section in document.exclusions:
        for list_item in section.items:
            for row_id in list_item.source_row_ids:
                if row_id:
                    mapping[row_id].append(list_item)
    return mapping


def _source_requires_exclusion_coverage(source: SourceRowRef) -> bool:
    status = str(source.commercial_status or "").strip().lower()
    reason = str(source.commercial_reason or "").strip().lower()
    if status in {"self_arranged", "excluded", "optional"}:
        return True
    if reason in {"cost_not_included", "self_arranged", "optional"}:
        return True
    text = "\n".join(
        value for value in (source.original_title, source.raw_text, source.title) if str(value or "").strip()
    ).lower()
    if has_self_transfer_marker(text) or "self arranged" in text or "self-arranged" in text:
        return True
    return bool(re.search(
        r"\b(?:price\s+not\s+included|cost\s+not\s+included|not\s+in(?:cl|lc)uded\s*[:?]|to\s+be\s+bought\s+on\s+site|paid\s+locally|pay\s+locally)\b",
        text,
        flags=re.IGNORECASE,
    ))


def _activity_signal_mismatch_warnings(
    *,
    source_text: str,
    label_text: str,
    row_id: str,
) -> list[ModelWarning]:
    warnings: list[ModelWarning] = []
    source_lower = source_text.lower()
    label_lower = label_text.lower()
    for signal_group in _SOURCE_SIGNAL_GROUPS:
        source_has_signal = any(signal in source_lower for signal in signal_group)
        label_has_signal = any(signal in label_lower for signal in signal_group)
        if source_has_signal and not label_has_signal:
            warnings.append(ModelWarning(
                code="inclusion_source_signal_missing_from_label",
                message=(
                    "An activity inclusion label appears to have lost an important source-row signal; "
                    "review for possible cross-row merge or overwritten title."
                ),
                severity="warning",
                source_row_ids=(row_id,),
            ))
            break
    return warnings


def _validate_inclusion_source_coverage(document: ItineraryDocument) -> list[ModelWarning]:
    """Check that included activities/accommodation remain visible in inclusions.

    This is the model-level guard for the class of bugs where a real activity is
    still present in the day itinerary but disappears from the inclusion list, or
    where one product's inclusion label is accidentally replaced by another row's
    title.  It only emits warnings because some future outputs may intentionally
    hide a source row, but every warning should be reviewed before a client PDF.
    """

    warnings: list[ModelWarning] = []
    source_by_id = {source.row_id: source for source in document.source_rows if source.row_id}
    inclusion_items_by_source = _inclusion_items_by_source_id(document)

    for item in document.items:
        if item.kind not in _REVIEW_KIND_COVERAGE or not _status_is_included(item.commercial_status):
            continue
        if not str(item.title or "").strip() or str(item.title or "").strip().lower() == "untitled item":
            continue
        for row_id in item.source_row_ids:
            if not row_id:
                continue
            inclusion_items = inclusion_items_by_source.get(row_id, [])
            if not inclusion_items:
                warnings.append(ModelWarning(
                    code="included_item_missing_inclusion_coverage",
                    message=(
                        "An included activity/accommodation item is linked to a day but has no matching "
                        "source-aware inclusion item."
                    ),
                    severity="warning",
                    source_row_ids=(row_id,),
                ))
                continue

            source_text = _source_text(source_by_id.get(row_id))
            item_text = _item_identity_text(item)
            support_tokens = _compact_tokens("\n".join([source_text, item_text]))
            source_tokens = _compact_tokens(source_text)
            for inclusion_item in inclusion_items:
                label_text = "\n".join([inclusion_item.label, *inclusion_item.detail_lines])
                label_tokens = _compact_tokens(label_text)
                if len(label_tokens) >= 2 and len(support_tokens) >= 2 and label_tokens.isdisjoint(support_tokens):
                    warnings.append(ModelWarning(
                        code="inclusion_label_not_supported_by_source",
                        message=(
                            "An inclusion label has little overlap with its linked source row; review for "
                            "possible title contamination from another product."
                        ),
                        severity="warning",
                        source_row_ids=(row_id,),
                    ))
                if len(label_tokens) >= 2 and len(source_tokens) >= 2 and label_tokens.isdisjoint(source_tokens):
                    warnings.append(ModelWarning(
                        code="inclusion_label_inferred_from_weak_source",
                        message=(
                            "An inclusion label is not directly supported by the supplier/source row text; "
                            "confirm the product name before final output."
                        ),
                        severity="warning",
                        source_row_ids=(row_id,),
                    ))
                warnings.extend(_activity_signal_mismatch_warnings(
                    source_text=source_text,
                    label_text=label_text,
                    row_id=row_id,
                ))

    return warnings


def _validate_exclusion_source_coverage(document: ItineraryDocument) -> list[ModelWarning]:
    """Warn when a commercial exclusion row loses its visible exclusion item."""

    warnings: list[ModelWarning] = []
    exclusion_items_by_source = _exclusion_items_by_source_id(document)
    for source in document.source_rows:
        if not source.row_id or not _source_requires_exclusion_coverage(source):
            continue
        if exclusion_items_by_source.get(source.row_id):
            continue
        warnings.append(ModelWarning(
            code="commercial_row_missing_exclusion_coverage",
            message=(
                "A self-arranged, optional or cost-not-included source row is not linked "
                "to a structured What's-not-included item."
            ),
            severity="warning",
            source_row_ids=(source.row_id,),
        ))
    return warnings


def _validate_duplicate_inclusion_sources(document: ItineraryDocument) -> list[ModelWarning]:
    """Warn when the same source row creates duplicate inclusion labels."""

    warnings: list[ModelWarning] = []
    seen: set[tuple[str, str]] = set()
    for section in document.inclusions:
        for list_item in section.items:
            label_key = " ".join(str(list_item.label or "").lower().split())
            if not label_key:
                continue
            for row_id in list_item.source_row_ids:
                key = (row_id, label_key)
                if key in seen:
                    warnings.append(ModelWarning(
                        code="duplicate_inclusion_for_source_row",
                        message="A source row produced the same inclusion label more than once.",
                        severity="warning",
                        source_row_ids=(row_id,),
                    ))
                seen.add(key)
    return warnings


def validate_itinerary_document(document: ItineraryDocument) -> tuple[ModelWarning, ...]:
    """Return model warnings/errors for source-row and day/item consistency."""

    warnings: list[ModelWarning] = []
    source_ids = [ref.row_id for ref in document.source_rows if ref.row_id]
    source_id_set = set(source_ids)
    item_ids = [item.item_id for item in document.items if item.item_id]
    item_id_set = set(item_ids)

    for row_id, count in Counter(source_ids).items():
        if count > 1:
            warnings.append(ModelWarning(
                code="duplicate_source_row_id",
                message="Two normalized rows share the same source row id.",
                severity="error",
                source_row_ids=(row_id,),
            ))

    for item_id, count in Counter(item_ids).items():
        if count > 1:
            warnings.append(ModelWarning(
                code="duplicate_document_item_id",
                message="Two document items share the same item id.",
                severity="error",
                source_row_ids=(item_id,),
            ))

    for item in document.items:
        missing_sources = tuple(row_id for row_id in item.source_row_ids if row_id not in source_id_set)
        if missing_sources:
            warnings.append(ModelWarning(
                code="item_missing_source_row",
                message="A document item references a source row that is not present in the document.",
                severity="error",
                source_row_ids=missing_sources,
            ))

    for day in document.days:
        missing_items = tuple(item_id for item_id in day.item_ids if item_id not in item_id_set)
        if missing_items:
            warnings.append(ModelWarning(
                code="day_missing_document_item",
                message="A day references a document item that is not present in the document.",
                severity="error",
                source_row_ids=missing_items,
            ))
        missing_sources = tuple(row_id for row_id in day.source_row_ids if row_id not in source_id_set)
        if missing_sources:
            warnings.append(ModelWarning(
                code="day_missing_source_row",
                message="A day references a source row that is not present in the document.",
                severity="error",
                source_row_ids=missing_sources,
            ))

    for section in (*document.inclusions, *document.exclusions):
        for list_item in section.items:
            missing_sources = tuple(row_id for row_id in list_item.source_row_ids if row_id not in source_id_set)
            if missing_sources:
                warnings.append(ModelWarning(
                    code="structured_list_item_missing_source_row",
                    message="A structured inclusion/exclusion item references a missing source row.",
                    severity="error",
                    source_row_ids=missing_sources,
                ))

    linked_item_ids = {item_id for day in document.days for item_id in day.item_ids}
    unlinked_included_items = tuple(
        item.item_id
        for item in document.items
        if _status_is_included(item.commercial_status) and item.item_id not in linked_item_ids
    )
    if unlinked_included_items:
        warnings.append(ModelWarning(
            code="included_items_not_linked_to_day",
            message="Included document items are not linked from any day.",
            severity="error",
            source_row_ids=unlinked_included_items[:20],
        ))

    warnings.extend(_validate_inclusion_source_coverage(document))
    warnings.extend(_validate_exclusion_source_coverage(document))
    warnings.extend(_validate_duplicate_inclusion_sources(document))

    return tuple(dict.fromkeys(warnings))
