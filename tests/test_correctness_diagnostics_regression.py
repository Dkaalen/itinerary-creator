"""Regression gates for Patch BZ1E correctness and diagnostics cleanup."""

from __future__ import annotations

import logging

import pytest

from itinerary_generation import health_report, quality_gate
from itinerary_generation.row_sequence import ordered_cities
from itinerary_generation.summaries import create_trip_glance
from pdf_exporter_modules.background_flowables import FullPageTint


def _group_tour_row(**overrides):
    row = {
        "day": "Day 1",
        "type": "Day Overview",
        "effective_type": "Day Overview",
        "city": "Reykjavik",
        "title": "Iceland holiday package",
        "original_title": "Small-group holiday package around Iceland",
        "details": "What's included",
        "is_optional": False,
        "commercial_status": "included",
    }
    row.update(overrides)
    return row


def test_trip_glance_reads_small_group_marker_from_original_title():
    row = _group_tour_row(
        title="Iceland holiday package",
        details="What's included",
        original_title="Small-group holiday package around Iceland",
    )

    glance = create_trip_glance([row], {"Day 1": [row]})

    assert glance["Travel Style"] == "Guided small-group tour"


def test_trip_glance_keeps_generic_group_tour_when_small_marker_is_absent():
    row = _group_tour_row(original_title="Guided holiday package around Iceland")

    glance = create_trip_glance([row], {"Day 1": [row]})

    assert glance["Travel Style"] == "Guided group tour"


def test_ordered_cities_is_shared_and_preserves_first_seen_order():
    rows = [
        {"city": " Oslo ", "type": "Hotel"},
        {"city": "Bergen", "type": "Hotel"},
        {"city": "Oslo", "type": "Hotel"},
        {"city": "", "type": "Hotel"},
        {"city": "Flåm", "type": "Hotel"},
        {"city": "Bergen", "type": "Hotel"},
    ]

    assert ordered_cities(rows) == ("Oslo", "Bergen", "Flåm")
    assert quality_gate.build_quality_snapshot(rows).input_cities == (
        "Oslo",
        "Bergen",
        "Flåm",
    )
    assert not hasattr(quality_gate, "_ordered_cities")
    assert not hasattr(health_report, "_ordered_cities")


class _CanvasBase:
    def __init__(self):
        self.saved = 0
        self.restored = 0
        self.rect_calls = 0
        self.fill_color = None

    def saveState(self):
        self.saved += 1

    def restoreState(self):
        self.restored += 1

    def setFillColor(self, color):
        self.fill_color = color

    def rect(self, *args, **kwargs):
        self.rect_calls += 1


class _UnsupportedAlphaCanvas(_CanvasBase):
    def setFillAlpha(self, alpha):
        raise NotImplementedError("alpha graphics state is unavailable")


class _InvalidAlphaCanvas(_CanvasBase):
    def setFillAlpha(self, alpha):
        raise ValueError("invalid alpha")


def test_full_page_tint_reports_unsupported_alpha_and_renders_opaque(caplog):
    canvas = _UnsupportedAlphaCanvas()
    tint = FullPageTint(alpha=0.72)

    with caplog.at_level(logging.WARNING, logger="pdf_exporter_modules.background_flowables"):
        tint.drawOn(canvas, 0, 0)

    assert canvas.saved == 1
    assert canvas.restored == 1
    assert canvas.rect_calls == 1
    assert "does not support fill transparency" in caplog.text


def test_full_page_tint_does_not_swallow_unexpected_alpha_errors():
    canvas = _InvalidAlphaCanvas()
    tint = FullPageTint(alpha=0.72)

    with pytest.raises(ValueError, match="invalid alpha"):
        tint.drawOn(canvas, 0, 0)

    assert canvas.saved == 1
    assert canvas.restored == 1
    assert canvas.rect_calls == 0
