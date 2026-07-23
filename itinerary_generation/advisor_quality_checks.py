"""Source-backed advisor checks for final client output.

The checks consume prepared render facts and source rows.  They never generate
replacement copy and therefore remain a downstream validation boundary.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Mapping

from itinerary_generation.client_quality_text import render_document_text
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue
from shared.source_rows import source_row_id
from shared.text import clean_space

_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private", re.compile(r"\bprivate\s+(?:transfer|tour|vehicle|guide|excursion)\b", re.I)),
    ("guided", re.compile(r"\b(?:guided\s+(?:tour|walk|visit)|english-speaking guide|professional guide)\b", re.I)),
    ("luxury", re.compile(r"\bluxury\b", re.I)),
    ("meal", re.compile(r"\b(?:lunch|dinner|breakfast|hot meal|meal)\s+(?:is\s+)?included\b", re.I)),
    ("admission", re.compile(r"\b(?:admission|entrance|entry)\s+(?:is\s+)?included\b", re.I)),
)
_GUARANTEE_RE = re.compile(
    r"\b(?:guaranteed?|will\s+(?:see|witness|spot)|promise[sd]?)\b.{0,80}\b(?:northern lights|aurora|whales?|wildlife)\b|"
    r"\b(?:northern lights|aurora|whales?|wildlife)\b.{0,80}\b(?:guaranteed?|will\s+(?:appear|be seen))\b",
    re.I,
)
_WEAK_FALLBACK_RE = re.compile(
    r"\b(?:the day[’']?s included arrangements(?: in .+?)? are listed below|"
    r"the day[’']?s arrangements are listed below|plans kept clear and easy to follow)\b",
    re.I,
)
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{4,}")
_STOP = {
    "activity", "experience", "included", "private", "guided", "tour", "transfer", "travel",
    "from", "with", "your", "into", "today", "visit", "city", "full", "half", "ticket",
}


def _text(value: object) -> str:
    return clean_space(value)


def _source_text(row: Mapping[str, Any]) -> str:
    values: list[str] = []
    for key in (
        "title", "original_title", "details", "description", "raw", "meeting_point",
        "pickup", "pick_up", "time", "display_time", "duration",
    ):
        values.append(_text(row.get(key)))
    for key in ("includes", "inclusions"):
        value = row.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(_text(item) for item in value)
        else:
            values.append(_text(value))
    return " ".join(value for value in values if value)


def _block_text(block: Any) -> str:
    parts = [
        _text(getattr(block, "section_title", "")),
        _text(getattr(block, "title", "")),
        _text(getattr(block, "description", "")),
    ]
    parts.extend(_text(value) for value in getattr(block, "includes", []) or [])
    parts.extend(_text(value) for value in getattr(block, "lines", []) or [])
    for meta in getattr(block, "meta", []) or []:
        parts.extend((_text(getattr(meta, "label", "")), _text(getattr(meta, "value", ""))))
    return " ".join(part for part in parts if part)


def _blocks_by_source_id(document: Any) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = {}
    for day in getattr(document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            ids = list(getattr(block, "source_row_ids", []) or [])
            row_id = _text(getattr(block, "row_id", ""))
            if row_id:
                ids.append(row_id)
            for source_id in ids:
                result.setdefault(str(source_id), []).append(block)
    return result


def _detail_value(row: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _text(row.get(key))
        if value and value.casefold() not in {"tbd", "tbc", "tba", "n/a", "unknown", "-"}:
            return value
    return ""


def _meaningful_tokens(value: str) -> set[str]:
    return {token.casefold() for token in _WORD_RE.findall(value) if token.casefold() not in _STOP}


def _product_fidelity_issues(document: Any, source_rows: Iterable[Mapping[str, Any]]) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    by_id = _blocks_by_source_id(document)
    for index, row in enumerate(source_rows or []):
        source_id = source_row_id(row, index)
        blocks = by_id.get(source_id, [])
        if not blocks:
            continue
        row_type = _text(row.get("effective_type") or row.get("type")).casefold()
        if row_type != "activity":
            continue
        source_title = _text(row.get("display_title") or row.get("title") or row.get("original_title"))
        if not source_title:
            continue
        source_tokens = _meaningful_tokens(source_title)
        output_tokens = _meaningful_tokens(" ".join(_block_text(block) for block in blocks))
        if len(source_tokens) >= 2 and output_tokens and not source_tokens.intersection(output_tokens):
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "product_identity_lost",
                    "A selected activity is no longer identifiable in the customer output.",
                    context=f"{source_id}: {source_title}",
                )
            )
    return issues


def _missing_detail_issues(document: Any, source_rows: Iterable[Mapping[str, Any]]) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    by_id = _blocks_by_source_id(document)
    fields = (
        ("meeting_point", ("meeting_point", "meeting", "pickup", "pick_up", "pickup_point"), "meeting point"),
        ("time", ("display_time", "time"), "time"),
        ("duration", ("duration",), "duration"),
    )
    for index, row in enumerate(source_rows or []):
        source_id = source_row_id(row, index)
        blocks = by_id.get(source_id, [])
        if not blocks:
            continue
        output = _text(" ".join(_block_text(block) for block in blocks)).casefold()
        for code_suffix, keys, label in fields:
            expected = _detail_value(row, keys)
            if not expected:
                continue
            # Exact formatting may change, so accept either the normalized
            # value or the semantic label in the matched product block.
            expected_norm = _text(expected).casefold()
            label_present = label in output
            value_tokens = _meaningful_tokens(expected_norm)
            value_present = expected_norm in output or (value_tokens and value_tokens.issubset(_meaningful_tokens(output)))
            if not label_present and not value_present:
                issues.append(
                    ItineraryValidationIssue(
                        WARNING,
                        f"missing_confirmed_{code_suffix}",
                        f"A confirmed product {label} is missing from the customer output.",
                        context=f"{source_id}: {expected}",
                    )
                )
    return issues


def _repetition_issues(document: Any) -> list[ItineraryValidationIssue]:
    intros = [_text(getattr(day, "intro", "")) for day in getattr(document, "days", []) or []]
    counts = Counter(value.casefold() for value in intros if value)
    repeated = [value for value, count in counts.items() if count >= 3]
    if not repeated:
        return []
    return [
        ItineraryValidationIssue(
            WARNING,
            "serious_copy_repetition",
            "Several itinerary days reuse the same customer-facing introduction.",
            context=repeated[0][:180],
        )
    ]


def advisor_quality_issues(document: Any, *, source_rows: Iterable[Mapping[str, Any]] | None = None) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    full_text = render_document_text(document)
    source_text = " ".join(_source_text(row) for row in source_rows or [])

    guarantee_match = _GUARANTEE_RE.search(full_text)
    if guarantee_match:
        context = full_text[max(0, guarantee_match.start() - 24): guarantee_match.end() + 24].casefold()
        if not any(marker in context for marker in ("cannot be guaranteed", "not guaranteed", "never guaranteed")):
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "unsupported_natural_phenomenon_guarantee",
                    "Customer copy guarantees a natural phenomenon or wildlife sighting.",
                )
            )
    if source_rows is not None:
        for claim, pattern in _CLAIM_PATTERNS:
            if pattern.search(full_text) and not re.search(rf"\b{re.escape(claim)}\b", source_text, flags=re.I):
                issues.append(
                    ItineraryValidationIssue(
                        BLOCKING,
                        f"unsupported_{claim}_claim",
                        f"Customer copy contains an unsupported {claim} claim.",
                    )
                )
    for day in getattr(document, "days", []) or []:
        intro = _text(getattr(day, "intro", ""))
        source = _text((getattr(day, "labels", {}) or {}).get("intro_decision_source", ""))
        if source == "admin_fallback_intro" or _WEAK_FALLBACK_RE.search(intro):
            issues.append(
                ItineraryValidationIssue(
                    WARNING,
                    "weak_generic_fallback",
                    "A day still relies on generic fallback copy and needs advisor review.",
                    context=f"{getattr(day, 'day', '')}: {intro}",
                )
            )
    issues.extend(_repetition_issues(document))
    if source_rows is not None:
        rows = [row for row in source_rows if isinstance(row, Mapping)]
        issues.extend(_product_fidelity_issues(document, rows))
        issues.extend(_missing_detail_issues(document, rows))
    return issues


__all__ = ["advisor_quality_issues"]
