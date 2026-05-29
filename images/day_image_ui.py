"""Preview/PDF marker rendering for day images."""

from __future__ import annotations

from pathlib import Path

from image_matcher import select_day_image
from images.image_overrides import CROP_FOCUS_OBJECT_POSITIONS, get_day_image_crop_focus
from images.image_preview import image_to_preview_data_uri
from images.image_bank import esc


def render_day_image_slot(day, rows, match=None, output_edits=None, *, image_bank_scan_paths):
    """Return the day-image marker used by the preview and PDF exporter."""
    if match is None:
        match = select_day_image(day, rows, image_bank_scan_paths)
    if not match:
        return ""

    image_path = match.get("path", "")
    crop_focus = get_day_image_crop_focus(output_edits, day)
    object_position = CROP_FOCUS_OBJECT_POSITIONS.get(crop_focus, CROP_FOCUS_OBJECT_POSITIONS["top"])
    data_uri = image_to_preview_data_uri(image_path)
    preview_img = ""
    if data_uri:
        preview_img = (
            f'<img class="day-image-preview-img" '
            f'style="object-position: {esc(object_position)};" '
            f'src="{esc(data_uri)}" alt="{esc(Path(image_path).stem)}" />'
        )

    return (
        f'<div class="day-image-slot" '
        f'data-image-path="{esc(image_path)}" '
        f'data-image-crop-focus="{esc(crop_focus)}" '
        f'data-image-score="{esc(match.get("score", ""))}" '
        f'data-image-reason="{esc(match.get("reason", ""))}">'
        f'{preview_img}'
        f'</div>'
    )
