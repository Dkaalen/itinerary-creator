"""Explainable decision contracts for generated client-facing copy.

The copy/title brains should not silently pick text. They return a traceable
contract internally, while the public writer functions keep returning plain text
for renderers and older callers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from shared.text import clean_space


@dataclass(frozen=True)
class CopyDecisionCandidate:
    """One possible client-facing text choice considered by a brain."""

    text: str
    source: str
    priority: int
    reason: str
    risk_flags: tuple[str, ...] = ()
    rejected_reason: str = ""

    def with_rejected_reason(self, reason: str) -> "CopyDecisionCandidate":
        return CopyDecisionCandidate(
            text=self.text,
            source=self.source,
            priority=self.priority,
            reason=self.reason,
            risk_flags=self.risk_flags,
            rejected_reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CopyDecisionTrace:
    """Selected text plus rejected alternatives and source metadata."""

    kind: str
    selected: CopyDecisionCandidate
    candidates: tuple[CopyDecisionCandidate, ...] = ()
    rejected: tuple[CopyDecisionCandidate, ...] = ()
    context: Mapping[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.selected.text

    @property
    def source(self) -> str:
        return self.selected.source

    @property
    def risk_flags(self) -> tuple[str, ...]:
        flags: list[str] = []
        for candidate in (self.selected, *self.rejected):
            flags.extend(candidate.risk_flags)
        return tuple(dict.fromkeys(flags))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "selected": self.selected.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "rejected": [candidate.to_dict() for candidate in self.rejected],
            "context": dict(self.context),
            "risk_flags": list(self.risk_flags),
        }

    def labels(self, prefix: str) -> dict[str, str]:
        """Return compact render labels for QA/review reports."""

        return {
            f"{prefix}_source": self.selected.source,
            f"{prefix}_reason": self.selected.reason,
            f"{prefix}_rejected_sources": ",".join(
                dict.fromkeys(candidate.source for candidate in self.rejected)
            ),
            f"{prefix}_risk_flags": ",".join(self.risk_flags),
        }


def clean_decision_text(value: object) -> str:
    return clean_space(value)


def decision_candidate(
    text: object,
    *,
    source: str,
    priority: int,
    reason: str,
    risk_flags: Iterable[str] = (),
) -> CopyDecisionCandidate | None:
    cleaned = clean_decision_text(text)
    if not cleaned:
        return None
    return CopyDecisionCandidate(
        text=cleaned,
        source=source,
        priority=priority,
        reason=reason,
        risk_flags=tuple(dict.fromkeys(flag for flag in risk_flags if flag)),
    )


def dedupe_candidates(candidates: Iterable[CopyDecisionCandidate | None]) -> tuple[CopyDecisionCandidate, ...]:
    """Deduplicate candidates by source/text while preserving order."""

    seen: set[tuple[str, str]] = set()
    result: list[CopyDecisionCandidate] = []
    for candidate in candidates:
        if candidate is None:
            continue
        key = (candidate.source, candidate.text.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return tuple(result)


def finalize_decision(
    *,
    kind: str,
    selected: CopyDecisionCandidate,
    candidates: Iterable[CopyDecisionCandidate | None] = (),
    context: Mapping[str, str] | None = None,
) -> CopyDecisionTrace:
    """Build a trace with selected and rejected candidates."""

    all_candidates = dedupe_candidates((selected, *tuple(candidates)))
    selected_key = (selected.source, selected.text.casefold())
    rejected: list[CopyDecisionCandidate] = []
    for candidate in all_candidates:
        if (candidate.source, candidate.text.casefold()) == selected_key:
            continue
        reason = _default_rejection_reason(selected, candidate)
        rejected.append(candidate.with_rejected_reason(reason))
    return CopyDecisionTrace(
        kind=kind,
        selected=selected,
        candidates=all_candidates,
        rejected=tuple(rejected),
        context=dict(context or {}),
    )


def _default_rejection_reason(selected: CopyDecisionCandidate, rejected: CopyDecisionCandidate) -> str:
    if "narrow_inclusion" in rejected.risk_flags and selected.priority >= rejected.priority:
        return "Narrow included/ticket item cannot outrank the broader selected day/product source."
    if rejected.priority < selected.priority:
        return "Lower-priority fallback source."
    if rejected.text.casefold() == selected.text.casefold():
        return "Duplicate wording from another source."
    return "Not selected by the day decision contract."


__all__ = [
    "CopyDecisionCandidate",
    "CopyDecisionTrace",
    "clean_decision_text",
    "decision_candidate",
    "dedupe_candidates",
    "finalize_decision",
]
