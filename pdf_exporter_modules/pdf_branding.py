"""Booknordics font and logo support for the shared typed PDF renderer."""
from __future__ import annotations

from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app_modules.output_brand import BOOKNORDICS_BRAND, BOOKNORDICS_LOGO_PATH, font_paths

CURRENT_OUTPUT_BRAND = "agent"
DM_FONT_NAMES = {
    "regular": "DMSans",
    "medium": "DMSans-Medium",
    "semibold": "DMSans-SemiBold",
    "bold": "DMSans-Bold",
}


def configure_pdf_brand(output_brand: str) -> None:
    global CURRENT_OUTPUT_BRAND
    CURRENT_OUTPUT_BRAND = output_brand if output_brand == BOOKNORDICS_BRAND else "agent"
    if CURRENT_OUTPUT_BRAND != BOOKNORDICS_BRAND:
        return
    paths = font_paths()
    for weight, font_name in DM_FONT_NAMES.items():
        path = paths[weight]
        if path.is_file() and font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(path)))


def is_booknordics_pdf() -> bool:
    return CURRENT_OUTPUT_BRAND == BOOKNORDICS_BRAND


def pdf_font(weight: str = "regular") -> str:
    if not is_booknordics_pdf():
        return "Helvetica-Bold" if weight in {"semibold", "bold"} else "Helvetica"
    requested = DM_FONT_NAMES.get(weight, DM_FONT_NAMES["regular"])
    if requested in pdfmetrics.getRegisteredFontNames():
        return requested
    return "Helvetica-Bold" if weight in {"semibold", "bold"} else "Helvetica"


def logo_path() -> Path | None:
    return BOOKNORDICS_LOGO_PATH if is_booknordics_pdf() and BOOKNORDICS_LOGO_PATH.is_file() else None
