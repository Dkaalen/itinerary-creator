"""Extract the final day-image contract from the rendered preview HTML.

The browser preview is the user's last reviewed visual source.  PDF export must
therefore consume the same selected image payload instead of re-selecting or
falling back to bundled defaults.  This module intentionally keeps the contract
small: day id, selected file path, embedded preview data URI and crop focus.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from bs4 import BeautifulSoup


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _image_data_uri(slot) -> str:
    image = slot.select_one("img.day-image-preview-img") if slot else None
    src = str(image.get("src", "") if image else "").strip()
    if re.match(r"^data:image/(?:jpeg|jpg|png|webp);base64,", src, flags=re.IGNORECASE):
        return src
    return ""


def day_image_matches_from_preview_html(html: str | None) -> dict[str, dict]:
    """Return day-image matches exactly as rendered in the current preview.

    If the preview contains embedded image data, the PDF exporter can use it as
    a parity fallback when the selected image path is unavailable in the export
    environment.  This prevents the typed PDF path from silently choosing a
    different Default-bank image.
    """

    if not html:
        return {}
    soup = BeautifulSoup(str(html), "html.parser")
    matches: dict[str, dict] = {}
    for page in soup.select(".a4-page.day-page[data-day]"):
        day = _clean(page.get("data-day"))
        if not day:
            continue
        slot = page.select_one(".day-image-slot")
        if not slot:
            continue
        path = str(slot.get("data-image-path", "") or "").strip()
        data_uri = _image_data_uri(slot)
        if not path and not data_uri:
            continue
        filename = Path(path).stem if path else "preview_image"
        bank_status = {
            "full_bank_found": str(slot.get("data-image-bank-full-found", "")).lower() == "true",
            "source_path": str(slot.get("data-image-bank-source-path", "") or ""),
        }
        is_default = str(slot.get("data-image-is-default", "")).lower() == "true" or "Default" in path.replace("\\", "/").split("/")
        matches[day] = {
            "day": day,
            "path": path,
            "data_uri": data_uri,
            "score": int(str(slot.get("data-image-score", "0") or "0") or 0),
            "reason": _clean(slot.get("data-image-reason", "preview image contract")) or "preview image contract",
            "city": _clean(slot.get("data-image-city", "")),
            "country": "",
            "filename": filename,
            "themes": [item for item in str(slot.get("data-image-themes", "") or "").split(",") if item],
            "seasons": [],
            "is_default": is_default,
            "is_generic": is_default,
            "image_bank_status": bank_status,
            "source_type": str(slot.get("data-image-source-type", "") or ("bundled_default" if is_default else "full_bank")),
            "fallback_reason": "",
            "score_breakdown": {
                "destination_score": 0,
                "activity_product_score": 0,
                "season_score": 0,
                "country_region_score": 0,
                "fallback_score": 0,
                "total_score": int(str(slot.get("data-image-score", "0") or "0") or 0),
            },
        }
    return matches


def merge_preview_image_contract(
    selected_matches: Mapping[str, Mapping | None] | None,
    preview_matches: Mapping[str, Mapping | None] | None,
    *,
    removed_days: set[str] | frozenset[str] | tuple[str, ...] = (),
) -> dict[str, Mapping | None]:
    """Prefer preview-selected images while preserving explicit removals.

    ``selected_matches`` comes from the server-side matcher/overrides.  The
    preview contract is preferred for days where the user has actually reviewed
    an image in the current preview, because it carries the embedded data URI
    needed for PDF parity.  Explicitly removed days stay empty even if an older
    preview HTML blob still contains an image marker.
    """

    explicitly_removed = {str(day) for day in (removed_days or ())}
    merged: dict[str, Mapping | None] = dict(selected_matches or {})
    for day, match in (preview_matches or {}).items():
        day_key = str(day)
        if day_key in explicitly_removed:
            merged[day_key] = None
            continue
        if match:
            merged[day_key] = dict(match)
    for day in explicitly_removed:
        merged[day] = None
    return merged
