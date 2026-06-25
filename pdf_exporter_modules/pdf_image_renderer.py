"""Image helpers for typed PDF export."""

from __future__ import annotations

from pathlib import Path
import base64
import re

from pdf_exporter_modules.image_constants import PDF_IMAGE_BOTTOM_Y
from pdf_exporter_modules.image_flowables import SamePageDayImage
from pdf_exporter_modules.image_layout import normalize_crop_focus


def image_path_from_match(image_match, temp_dir):
    """Resolve a PDF image source from the final preview image contract."""

    if not image_match or not temp_dir:
        return None
    path = Path(str(image_match.get("path", "") or ""))
    if path.exists() and path.is_file():
        return path
    data_uri = str(image_match.get("data_uri", "") or "").strip()
    match = re.match(r"^data:image/(?:jpeg|jpg|png|webp);base64,(.+)$", data_uri, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    temp_path = Path(temp_dir) / f"preview_contract_day_image_{abs(hash(data_uri)) % 10_000_000}.img"
    try:
        temp_path.write_bytes(base64.b64decode(match.group(1)))
        return temp_path
    except (OSError, ValueError):
        return None


def render_day_image_flowable(image_match, crop_focus, temp_dir, doc):
    if not (image_match and temp_dir and doc):
        return None
    path = image_path_from_match(image_match, temp_dir)
    if not (path and path.exists() and path.is_file()):
        return None
    return SamePageDayImage(
        source_path=path,
        temp_dir=temp_dir,
        x=0,
        content_top_y=doc.pagesize[1] - doc.topMargin,
        content_width=doc.pagesize[0],
        content_height=doc.height,
        page_height=doc.pagesize[1],
        bottom_y=PDF_IMAGE_BOTTOM_Y,
        crop_focus=normalize_crop_focus(crop_focus),
    )
