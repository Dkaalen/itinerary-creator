"""Output-brand themes shared by preview and PDF rendering."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Mapping

AGENT_BRAND = "agent"
BOOKNORDICS_BRAND = "booknordics_customer"

_ROOT = Path(__file__).resolve().parents[1]
BOOKNORDICS_LOGO_PATH = _ROOT / "assets" / "brands" / "booknordics-logo.png"
DM_SANS_DIR = _ROOT / "assets" / "fonts" / "dm-sans"


def output_brand_id(output_edits: Mapping[str, Any] | None) -> str:
    value = str((output_edits or {}).get("output_brand") or AGENT_BRAND).strip()
    return value if value in {AGENT_BRAND, BOOKNORDICS_BRAND} else AGENT_BRAND


def is_booknordics(output_edits: Mapping[str, Any] | None) -> bool:
    return output_brand_id(output_edits) == BOOKNORDICS_BRAND


def logo_data_uri(output_edits: Mapping[str, Any] | None) -> str:
    if not is_booknordics(output_edits) or not BOOKNORDICS_LOGO_PATH.is_file():
        return ""
    encoded = base64.b64encode(BOOKNORDICS_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def font_paths() -> dict[str, Path]:
    return {
        "regular": DM_SANS_DIR / "DMSans-Regular.ttf",
        "medium": DM_SANS_DIR / "DMSans-Medium.ttf",
        "semibold": DM_SANS_DIR / "DMSans-SemiBold.ttf",
        "bold": DM_SANS_DIR / "DMSans-Bold.ttf",
    }
