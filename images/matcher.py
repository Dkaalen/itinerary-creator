"""Destination-first image matching and day-image selection."""

from __future__ import annotations

from images.matcher_context import build_day_context
from images.matcher_scoring import (
    candidate_destination_matches,
    candidate_to_payload,
    score_image_for_day,
    season_available_for_context,
)
from images.matcher_selection import select_best_candidate_for_context, select_day_image, select_day_images


# Backwards-compatible private aliases for callers/tests that may have imported them.
_candidate_destination_matches = candidate_destination_matches
_season_available_for_context = season_available_for_context
_candidate_to_payload = candidate_to_payload
_select_best_candidate_for_context = select_best_candidate_for_context
