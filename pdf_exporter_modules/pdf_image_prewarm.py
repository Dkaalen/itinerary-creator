"""Pre-build PDF image crop variants before ReportLab starts drawing pages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import diagnostics

from pdf_exporter_modules.image_constants import PDF_IMAGE_BOTTOM_Y, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT
from pdf_exporter_modules.image_layout import make_cover_cropped_image, normalize_crop_focus
from pdf_exporter_modules.pdf_day_renderer import render_day_story
from pdf_exporter_modules.pdf_image_renderer import image_path_from_match
from pdf_exporter_modules.story import story_height


def _day_image_height_for_story(story: Sequence, doc) -> float | None:
    if not (story and doc):
        return None
    try:
        used_height = story_height(story, doc.width)
    except Exception as error:
        diagnostics.warn_exception(
            "pdf_image_prewarm",
            "PDF day-image prewarm height calculation failed; export will continue without prewarming this image.",
            error,
            source="pdf_exporter_modules.pdf_image_prewarm",
        )
        return None
    text_bottom_y = float(doc.pagesize[1] - doc.topMargin) - float(used_height)
    image_top_y = min(
        text_bottom_y - PDF_IMAGE_GAP,
        (float(doc.pagesize[1]) / 2.0) - PDF_IMAGE_HALF_OFFSET,
    )
    image_height = image_top_y - PDF_IMAGE_BOTTOM_Y
    return image_height if image_height >= PDF_MIN_IMAGE_HEIGHT else None


def _prewarm_day_image(day, styles, *, image_match, crop_focus: str, temp_dir, doc, min_compact_level: int = 0) -> bool:
    path = image_path_from_match(image_match, temp_dir)
    if not (path and path.exists() and path.is_file()):
        return False

    for compact_level in range(max(0, int(min_compact_level or 0)), 4):
        story = render_day_story(day, styles, compact_level=compact_level)
        image_height = _day_image_height_for_story(story, doc)
        if image_height is None:
            continue
        cropped = make_cover_cropped_image(
            path,
            float(doc.pagesize[0]),
            image_height,
            temp_dir,
            crop_focus=normalize_crop_focus(crop_focus),
        )
        return bool(cropped)
    return False


def prewarm_pdf_day_images(
    days: Sequence,
    styles,
    *,
    day_images: Mapping[str, Mapping | None] | None,
    day_image_crop_focus: Mapping[str, str] | None,
    temp_dir,
    doc,
    min_compact_level: int = 0,
) -> int:
    """Warm persistent crop cache for day images and return warmed count.

    ReportLab normally calls image cropping from ``drawOn`` while building the
    document.  Doing the deterministic crop work before ``doc.build`` makes the
    first export less bursty and keeps subsequent exports fast through the
    persistent image cache.
    """

    if not (days and day_images and temp_dir and doc):
        return 0
    warmed = 0
    for day in days:
        day_key = getattr(day, "day", "")
        image_match = (day_images or {}).get(day_key)
        if not image_match:
            continue
        crop_focus = (day_image_crop_focus or {}).get(day_key, "top") if day_image_crop_focus else "top"
        try:
            if _prewarm_day_image(
                day,
                styles,
                image_match=image_match,
                crop_focus=crop_focus,
                temp_dir=temp_dir,
                doc=doc,
                min_compact_level=min_compact_level,
            ):
                warmed += 1
        except Exception as error:
            # Pre-warming is an optimization only. The normal PDF flowable still
            # performs its own safe image handling during document build.
            diagnostics.warn_exception(
                "pdf_image_prewarm",
                "PDF day-image prewarm failed; export will continue with normal image handling.",
                error,
                raw_value=day_key,
                source="pdf_exporter_modules.pdf_image_prewarm",
            )
            continue
    return warmed


__all__ = ["prewarm_pdf_day_images"]
