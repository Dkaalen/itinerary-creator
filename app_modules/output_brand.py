"""Output-brand themes and shared brand assets for preview/PDF rendering."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Mapping

AGENT_BRAND = "agent"
BOOKNORDICS_BRAND = "booknordics_customer"

BOOKNORDICS_COLORS = {
    "page_bg": "#FAFAFB",
    "preview_bg": "#00193C",
    "ink": "#00193C",
    "body": "#202738",
    "muted": "#667085",
    "line": "#D7DDE5",
    "card": "rgba(255, 255, 255, 0.88)",
    "accent": "#FF0041",
}

_ROOT = Path(__file__).resolve().parents[1]
BOOKNORDICS_LOGO_PATH = _ROOT / "assets" / "brands" / "booknordics-logo.png"
BOOKNORDICS_SYMBOL_PATH = _ROOT / "assets" / "brands" / "booknordics-symbol.png"
DM_SANS_DIR = _ROOT / "assets" / "fonts" / "dm-sans"


def output_brand_id(output_edits: Mapping[str, Any] | None) -> str:
    value = str((output_edits or {}).get("output_brand") or AGENT_BRAND).strip()
    return value if value in {AGENT_BRAND, BOOKNORDICS_BRAND} else AGENT_BRAND


def is_booknordics(output_edits: Mapping[str, Any] | None) -> bool:
    return output_brand_id(output_edits) == BOOKNORDICS_BRAND


def _file_data_uri(path: Path, mime_type: str) -> str:
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def logo_data_uri(output_edits: Mapping[str, Any] | None) -> str:
    if not is_booknordics(output_edits):
        return ""
    return _file_data_uri(BOOKNORDICS_LOGO_PATH, "image/png")


def font_paths() -> dict[str, Path]:
    return {
        "regular": DM_SANS_DIR / "DMSans-Regular.ttf",
        "medium": DM_SANS_DIR / "DMSans-Medium.ttf",
        "semibold": DM_SANS_DIR / "DMSans-SemiBold.ttf",
        "bold": DM_SANS_DIR / "DMSans-Bold.ttf",
    }


def dm_sans_font_face_css(output_brand: str) -> str:
    """Return embeddable DM Sans font-face rules for browser previews."""

    if output_brand != BOOKNORDICS_BRAND:
        return ""

    weights = {
        "regular": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700",
    }
    rules: list[str] = []
    for weight, css_weight in weights.items():
        data_uri = _file_data_uri(font_paths()[weight], "font/ttf")
        if not data_uri:
            continue
        rules.append(
            "@font-face {"
            "font-family: 'DM Sans';"
            f"src: url('{data_uri}') format('truetype');"
            f"font-weight: {css_weight};"
            "font-style: normal;"
            "font-display: swap;"
            "}"
        )
    return "\n".join(rules)


def editor_brand_payload(output_edits: Mapping[str, Any] | None, colors: Mapping[str, str] | None) -> dict[str, Any]:
    """Return the brand contract consumed by the visual editor."""

    output_brand = output_brand_id(output_edits)
    effective_colors = colors or (BOOKNORDICS_COLORS if output_brand == BOOKNORDICS_BRAND else {})
    return {
        "output_brand": output_brand,
        "colors": dict(effective_colors),
        "logo_data_uri": logo_data_uri(output_edits),
        "font_face_css": dm_sans_font_face_css(output_brand),
    }
