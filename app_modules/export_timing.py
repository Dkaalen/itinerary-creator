"""Internal timing capture for PDF export stages."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Any, Iterator, MutableMapping

PDF_EXPORT_TIMINGS_KEY = "_pdf_export_timings"


def reset_pdf_export_timings(state: MutableMapping[str, Any]) -> None:
    """Start a fresh timing record for one PDF export attempt."""

    state[PDF_EXPORT_TIMINGS_KEY] = []


@contextmanager
def record_pdf_export_stage(state: MutableMapping[str, Any], stage: str) -> Iterator[None]:
    """Record elapsed seconds for a named export stage."""

    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        timings = state.setdefault(PDF_EXPORT_TIMINGS_KEY, [])
        if isinstance(timings, list):
            timings.append({"stage": str(stage), "seconds": round(elapsed, 4)})


def pdf_export_timings(state: MutableMapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the latest export timing records."""

    value = state.get(PDF_EXPORT_TIMINGS_KEY)
    if not isinstance(value, list):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))
