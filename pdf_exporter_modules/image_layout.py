"""PDF image crop and layout helpers."""

from pathlib import Path

import diagnostics

try:
    from PIL import Image as PILImage, ImageOps
except ImportError:  # pragma: no cover - export safely skips images if Pillow is unavailable
    PILImage = None
    ImageOps = None

from .image_constants import PDF_CROP_FOCUS_FACTORS, PDF_CROP_VERTICAL_FOCUS, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT


def calculate_day_image_layout(
    used_height,
    content_height,
    gap=PDF_IMAGE_GAP,
    half_offset=PDF_IMAGE_HALF_OFFSET,
    min_height=PDF_MIN_IMAGE_HEIGHT,
    bottom_bleed=0,
):
    """Return spacer/image height for lower-half day imagery, or None."""
    image_top = max(float(used_height) + float(gap), (float(content_height) / 2.0) + float(half_offset))
    image_height = float(content_height) + float(bottom_bleed) - image_top
    if image_height < float(min_height):
        return None
    spacer_height = max(0, image_top - float(used_height))
    return spacer_height, image_height


def normalize_crop_focus(value):
    value = str(value or "").strip().lower()
    if value in PDF_CROP_FOCUS_FACTORS:
        return value
    if value in {"upper", "sky", "aurora"}:
        return "top"
    if value in {"lower"}:
        return "bottom"
    return "top"


def make_cover_cropped_image(source_path, target_width, target_height, temp_dir, crop_focus="top"):
    """Create a temporary cover-cropped image matching the PDF box ratio."""
    if PILImage is None or ImageOps is None:
        return None

    try:
        with PILImage.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            source_width, source_height = image.size
            if source_width <= 0 or source_height <= 0 or target_width <= 0 or target_height <= 0:
                return None

            target_ratio = float(target_width) / float(target_height)
            source_ratio = float(source_width) / float(source_height)

            if source_ratio > target_ratio:
                crop_width = max(1, int(source_height * target_ratio))
                left = max(0, int((source_width - crop_width) / 2))
                box = (left, 0, min(source_width, left + crop_width), source_height)
            else:
                crop_height = max(1, int(source_width / target_ratio))
                extra_height = max(0, source_height - crop_height)
                focus = PDF_CROP_FOCUS_FACTORS.get(normalize_crop_focus(crop_focus), PDF_CROP_VERTICAL_FOCUS)
                top = max(0, int(extra_height * focus))
                box = (0, top, source_width, min(source_height, top + crop_height))

            image = image.crop(box)

            # ReportLab embeds the actual source pixels. Crop-only temp files can
            # keep multi-megapixel originals and inflate client PDFs massively.
            # Resize to roughly 2x the displayed point size, which is sharp for
            # A4 output while keeping file sizes emailable.
            target_px = (
                max(1, int(float(target_width) * 2.0)),
                max(1, int(float(target_height) * 2.0)),
            )
            if image.size != target_px:
                image = image.resize(target_px, PILImage.LANCZOS)

            temp_path = Path(temp_dir) / (
                f"day_image_{abs(hash((str(source_path), round(float(target_width), 2), round(float(target_height), 2), normalize_crop_focus(crop_focus)))) % 10_000_000}.jpg"
            )
            image.save(temp_path, format="JPEG", quality=76, optimize=True)
            return temp_path
    except (OSError, ValueError) as error:
        diagnostics.warn_exception("pdf_image", "Could not crop image for PDF output.", error, str(source_path), source="pdf_exporter_modules.image_layout")
        return None
