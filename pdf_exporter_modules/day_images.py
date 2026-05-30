"""Day-page image insertion helpers."""

import base64
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4

from .image_constants import PDF_IMAGE_BOTTOM_Y
from .image_flowables import SamePageDayImage
from .image_layout import normalize_crop_focus
from .image_paths import resolve_image_path


def _image_path_from_embedded_data_uri(slot, temp_dir):
    """Return a temp image path from the preview data URI when file paths fail.

    The browser preview embeds the selected image as a data URI. The ReportLab
    PDF renderer normally reads ``data-image-path`` from disk, but that can fail
    in zip/submodule/deployment layouts. Falling back to the same embedded data
    URI keeps preview and PDF on the same selected image instead of silently
    reverting to generic artwork.
    """
    image = slot.select_one("img.day-image-preview-img") if slot else None
    raw_src = image.get("src", "") if image else ""
    match = re.match(r"^data:image/(?:jpeg|jpg|png|webp);base64,(.+)$", raw_src, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    try:
        temp_path = Path(temp_dir) / f"embedded_day_image_{abs(hash(raw_src)) % 10_000_000}.img"
        temp_path.write_bytes(base64.b64decode(match.group(1)))
        return temp_path
    except Exception:
        return None


def add_day_image_if_possible(
    page,
    page_story,
    html_path,
    temp_dir,
    available_width,
    available_height,
    measurement_story=None,
    left_margin=0,
    top_margin=0,
):
    """Add a same-page lower-half edge-to-edge day image when a match exists."""
    slot = page.select_one(".day-image-slot")
    if not slot:
        return

    image_path = resolve_image_path(slot.get("data-image-path"), html_path)
    if not image_path:
        image_path = _image_path_from_embedded_data_uri(slot, temp_dir)
    if not image_path:
        return

    crop_focus = normalize_crop_focus(slot.get("data-image-crop-focus", "top"))

    page_story.append(
        SamePageDayImage(
            source_path=image_path,
            temp_dir=temp_dir,
            x=0,
            content_top_y=A4[1] - top_margin,
            content_width=A4[0],
            content_height=available_height,
            page_height=A4[1],
            bottom_y=PDF_IMAGE_BOTTOM_Y,
            crop_focus=crop_focus,
        )
    )
