"""Output-brand cover text palette helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app_modules.output_brand import BOOKNORDICS_BRAND, BOOKNORDICS_COLORS
from itinerary_generation.cover_contrast import cover_text_area_is_dark

_BOOKNORDICS_LIGHT_TEXT = {
    "ink": "#FAFAFB",
    "muted": "#D7DDE5",
}


def apply_output_brand_cover_palette(cover_theme: Mapping[str, Any], output_brand: str) -> dict[str, Any]:
    """Return cover theme data adjusted for the selected output brand."""

    theme = dict(cover_theme or {})
    if output_brand != BOOKNORDICS_BRAND:
        return theme

    is_dark = cover_text_area_is_dark(
        theme.get("background_path") or "",
        str(theme.get("background_crop_focus") or "top"),
    )
    if is_dark is True:
        theme.update(_BOOKNORDICS_LIGHT_TEXT)
        theme["cover_text_mode"] = "light"
    else:
        theme.update({
            "ink": BOOKNORDICS_COLORS["ink"],
            "muted": BOOKNORDICS_COLORS["muted"],
            "cover_text_mode": "dark",
        })
    theme["accent"] = BOOKNORDICS_COLORS["accent"]
    return theme
