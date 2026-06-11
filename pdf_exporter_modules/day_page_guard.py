"""One-page day layout safeguards for PDF exports.

Day pages are a client-facing contract: a day heading, its arrangements and its
activity details must not spill onto an unlabelled continuation page. The PDF
renderers use ReportLab flowables, so this module provides one shared preflight
check before a rendered day story is appended to the document story.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from reportlab.platypus import Flowable, KeepTogether

from .story import story_height


@dataclass(frozen=True)
class DayPageLayoutResult:
    """Measured result for a day-page story."""

    label: str
    used_height: float
    available_height: float
    fits: bool


class PdfDayLayoutError(ValueError):
    """Raised when a day cannot safely fit inside one PDF page."""


# ReportLab wrap measurements can differ by a few points from final layout due
# table rounding and paragraph internals. Keep the tolerance small: enough to
# avoid false positives, not enough to allow visible continuation pages.
_HEIGHT_TOLERANCE = 6.0


def measure_day_story(flowables: Iterable[Flowable], available_width: float, available_height: float, *, label: str = "Day") -> DayPageLayoutResult:
    """Measure whether the given day story fits on one PDF page."""

    used_height = float(story_height(list(flowables), available_width))
    available_height = float(available_height)
    return DayPageLayoutResult(
        label=str(label or "Day"),
        used_height=used_height,
        available_height=available_height,
        fits=used_height <= available_height + _HEIGHT_TOLERANCE,
    )


def assert_day_story_fits_one_page(flowables: list[Flowable], available_width: float, available_height: float, *, label: str = "Day") -> DayPageLayoutResult:
    """Raise a clear error instead of allowing a silent split-day PDF."""

    result = measure_day_story(flowables, available_width, available_height, label=label)
    if not result.fits:
        raise PdfDayLayoutError(
            f"{result.label} is too tall for one PDF day page "
            f"({result.used_height:.1f} pt used / {result.available_height:.1f} pt available). "
            "Shorten the day text, remove optional notes, or reduce activity details before exporting."
        )
    return result


def one_page_day_flowable(flowables: list[Flowable], available_width: float, available_height: float, *, label: str = "Day") -> KeepTogether:
    """Validate then return a flowable that keeps the complete day together."""

    assert_day_story_fits_one_page(flowables, available_width, available_height, label=label)
    return KeepTogether(flowables)
