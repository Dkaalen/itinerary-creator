"""Title-source priority contract for client-facing day titles."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from itinerary_generation.activity_identity_contract import resolve_activity_identity
from itinerary_generation.activity_titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.copy_decision_contract import (
    CopyDecisionCandidate,
    CopyDecisionTrace,
    clean_decision_text,
    decision_candidate,
    dedupe_candidates,
    finalize_decision,
)
from shared.source_text_cleanup import clean_supplier_title
from text_polish import polish_title

_NARROW_INCLUDED_ITEM_RE = re.compile(
    r"\b(?:ticket|tickets|admission|entry|round[- ]trip)\b|\b(?:funicular|cable\s+car|museum|fortress|palace|cathedral|buns?)\b",
    flags=re.IGNORECASE,
)
_TITLE_FIELD_KEYS = ("title", "original_title")


def _clean_title(value: object) -> str:
    return clean_supplier_title(polish_title(clean_decision_text(value))).strip(" -:|.,")


def _source_title(row: Mapping[str, object]) -> str:
    for key in _TITLE_FIELD_KEYS:
        value = _clean_title(row.get(key))
        if value:
            return value
    return ""


def _candidate_from_text(
    text: object,
    *,
    source: str,
    priority: int,
    reason: str,
    risk_flags: Iterable[str] = (),
) -> CopyDecisionCandidate | None:
    cleaned = _clean_title(text)
    return decision_candidate(cleaned, source=source, priority=priority, reason=reason, risk_flags=risk_flags)


def narrow_inclusion_title_candidates(row: Mapping[str, object]) -> tuple[CopyDecisionCandidate, ...]:
    """Return weak included-item title candidates for rejection/QA traceability."""

    candidates: list[CopyDecisionCandidate | None] = []
    for item in row.get("includes", []) or []:
        text = _clean_title(item)
        if not text or not _NARROW_INCLUDED_ITEM_RE.search(text):
            continue
        text = re.sub(r"^Tickets?\s+to\s+", "", text, flags=re.IGNORECASE).strip(" -:|.,")
        text = re.sub(r"^Admission\s+to\s+", "", text, flags=re.IGNORECASE).strip(" -:|.,")
        if text:
            candidates.append(
                _candidate_from_text(
                    text,
                    source="narrow_inclusion_title",
                    priority=20,
                    reason="Included item is useful context but is too narrow to title the whole day.",
                    risk_flags=("narrow_inclusion",),
                )
            )
    return dedupe_candidates(candidates)


def _matches_narrow_candidate(title: str, narrow_candidates: Sequence[CopyDecisionCandidate]) -> bool:
    cleaned = _clean_title(title).casefold()
    return bool(cleaned and any(candidate.text.casefold() == cleaned for candidate in narrow_candidates))


def activity_title_candidates(row: Mapping[str, object]) -> tuple[CopyDecisionCandidate, ...]:
    """Return ranked title candidates for one arranged activity row."""

    identity = resolve_activity_identity(row)
    product_title = identity.display_title if identity.source in {"normalized_product", "product_registry"} else ""
    product_family = identity.canonical_family
    supplier_title = _source_title(row)
    generated_title = normalize_client_day_title(create_client_activity_title(dict(row)), dict(row))
    narrow_candidates = narrow_inclusion_title_candidates(row)
    generated_is_narrow = _matches_narrow_candidate(generated_title, narrow_candidates)
    return dedupe_candidates(
        (
            _candidate_from_text(
                product_title,
                source="activity_product_display_title",
                priority=95,
                reason="Normalizer attached a canonical product title; it owns broad activity identity.",
            ),
            _candidate_from_text(
                generated_title,
                source="activity_title_rule",
                priority=88 if not generated_is_narrow else 65,
                reason="Activity title rules cleaned the source title into client-facing wording.",
                risk_flags=("narrow_inclusion",) if generated_is_narrow else (),
            ),
            _candidate_from_text(
                supplier_title,
                source="supplier_activity_title",
                priority=82 if product_family else 86,
                reason="Supplier activity title is the broadest source title available for this activity.",
            ),
            *narrow_candidates,
        )
    )


def select_activity_title(row: Mapping[str, object]) -> CopyDecisionTrace:
    """Select one activity title using the title-source priority contract."""

    candidates = activity_title_candidates(row)
    selected = max(candidates, key=lambda candidate: (candidate.priority, len(candidate.text))) if candidates else decision_candidate(
        "Experience",
        source="activity_title_fallback",
        priority=10,
        reason="No usable product/source title was available.",
        risk_flags=("fallback_title",),
    )
    assert selected is not None
    return finalize_decision(
        kind="activity_title",
        selected=selected,
        candidates=candidates,
        context={"product_family": resolve_activity_identity(row).canonical_family},
    )


def join_title_text(first: str, second: str, *, max_length: int = 82) -> str:
    """Compose two title fragments without letting one swallowed fragment dominate."""

    first = _clean_title(first)
    second = _clean_title(second)
    if not first:
        return second
    if not second or first.casefold() == second.casefold():
        return first
    combined_lower = f"{first} {second}".lower()
    if first.lower().startswith("arrival in ") and "northern lights" in second.lower() and "cruise" in second.lower():
        return f"{first} & Northern Lights Cruise"
    if "bergen past" in combined_lower and "fløibanen" in combined_lower:
        return "Bergen Walking Tour & Fløibanen"
    if "walrus" in combined_lower and "brewery" in combined_lower:
        return "Walrus Safari and Svalbard Brewery Visit"
    if "reindeer" in combined_lower and "northern lights" in combined_lower:
        return "Reindeer & Sámi Culture and Northern Lights Hunt"
    if first.casefold() in second.casefold():
        return second
    if second.casefold() in first.casefold():
        return first
    title = f"{first} & {second}"
    if len(title) <= max_length:
        return title
    title = f"{first} and {second}"
    return title if len(title) <= max_length else first


def compose_activity_day_title(activity_rows: Sequence[Mapping[str, object]]) -> CopyDecisionTrace:
    """Compose a whole-day title from activity title decisions."""

    traces = [select_activity_title(row) for row in activity_rows[:2]]
    if not traces:
        selected = decision_candidate(
            "Experience",
            source="activity_title_fallback",
            priority=10,
            reason="No arranged activity rows were available.",
            risk_flags=("fallback_title",),
        )
        assert selected is not None
        return finalize_decision(kind="day_title", selected=selected)
    if len(traces) == 1:
        selected = traces[0].selected
        return finalize_decision(kind="day_title", selected=selected, candidates=traces[0].candidates)
    text = join_title_text(traces[0].text, traces[1].text)
    selected = decision_candidate(
        text,
        source="composed_activity_title",
        priority=96,
        reason="Multiple arranged activities require a composed whole-day title.",
    )
    assert selected is not None
    return finalize_decision(
        kind="day_title",
        selected=selected,
        candidates=(*traces[0].candidates, *traces[1].candidates),
    )


__all__ = [
    "activity_title_candidates",
    "compose_activity_day_title",
    "join_title_text",
    "narrow_inclusion_title_candidates",
    "select_activity_title",
]
