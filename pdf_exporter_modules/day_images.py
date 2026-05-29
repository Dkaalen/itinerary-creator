"""Day-page image insertion helpers."""

from reportlab.lib.pagesizes import A4

from .image_constants import PDF_IMAGE_BOTTOM_Y
from .image_flowables import SamePageDayImage
from .image_layout import normalize_crop_focus
from .image_paths import resolve_image_path


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
