"""Lazy public surface for itinerary row normalization."""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = (
    "normalize_row",
    "normalize_itinerary_rows",
    "warn_suspicious_city",
)


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".core", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
