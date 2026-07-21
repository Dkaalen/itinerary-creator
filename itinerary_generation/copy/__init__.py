"""Lazy deterministic client-facing copy composition helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = (
    "DayVisitContext",
    "build_day_visit_contexts",
    "client_activity_intro",
    "client_group_tour_intro",
)

_EXPORTS = {
    "DayVisitContext": ("visit_context", "DayVisitContext"),
    "build_day_visit_contexts": ("visit_context", "build_day_visit_contexts"),
    "client_activity_intro": ("activity_composition", "client_activity_intro"),
    "client_group_tour_intro": ("activity_composition", "client_group_tour_intro"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
