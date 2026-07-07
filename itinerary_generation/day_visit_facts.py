"""Visit-memory adapter for day facts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisitFacts:
    """Normalized visit-memory values for one day."""

    return_visit: bool = False
    visit_number: int = 1
    previous_visit_days: tuple[str, ...] = ()


def build_visit_facts(visit_context: object | None = None) -> VisitFacts:
    """Return visit-memory facts without coupling DayFacts to a context class."""

    return VisitFacts(
        return_visit=bool(getattr(visit_context, "is_return_visit", False)),
        visit_number=int(getattr(visit_context, "visit_number", 1) or 1),
        previous_visit_days=tuple(getattr(visit_context, "previous_days", ()) or ()),
    )


__all__ = ["VisitFacts", "build_visit_facts"]
