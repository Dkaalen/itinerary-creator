"""PDF image crop and layout helpers."""

from pathlib import Path
import hashlib
import os
import shutil
import tempfile

import diagnostics

try:
    from PIL import Image as PILImage, ImageOps
except ImportError:  # pragma: no cover - export safely skips images if Pillow is unavailable
    PILImage = None
    ImageOps = None

from .image_constants import PDF_CROP_FOCUS_FACTORS, PDF_CROP_VERTICAL_FOCUS, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT




def _source_signature(source_path: Path) -> tuple[str, int, int]:
    try:
        resolved = str(source_path.resolve())
    except OSError:
        resolved = str(source_path)
    try:
        stat = source_path.stat()
    except OSError:
        return resolved, 0, 0
    return resolved, int(stat.st_mtime_ns), int(stat.st_size)


def _persistent_pdf_image_cache_dir() -> Path | None:
    if str(os.environ.get("ITINERARY_DISABLE_PDF_IMAGE_CACHE", "")).strip().lower() in {"1", "true", "yes"}:
        return None
    root = Path(tempfile.gettempdir()) / "itinerary_pdf_image_cache"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return root


def _cached_variant_path(source_path, target_width, target_height, crop_focus) -> Path | None:
    cache_dir = _persistent_pdf_image_cache_dir()
    if cache_dir is None:
        return None
    resolved, mtime_ns, size = _source_signature(Path(source_path))
    digest = hashlib.sha1(
        f"{resolved}|{mtime_ns}|{size}|{round(float(target_width), 2)}|{round(float(target_height), 2)}|{crop_focus}|v2".encode("utf-8", "surrogateescape")
    ).hexdigest()[:24]
    return cache_dir / f"{digest}.jpg"


def _copy_cached_variant(cache_path: Path, temp_path: Path) -> Path | None:
    if not cache_path.exists():
        return None
    try:
        if not temp_path.exists():
            shutil.copy2(cache_path, temp_path)
        return temp_path
    except OSError:
        return cache_path if cache_path.exists() else None


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

    normalized_focus = normalize_crop_focus(crop_focus)
    cache_path = _cached_variant_path(source_path, target_width, target_height, normalized_focus)
    cache_token = cache_path.stem if cache_path else str(abs(hash((str(source_path), round(float(target_width), 2), round(float(target_height), 2), normalized_focus))) % 10_000_000)
    temp_path = Path(temp_dir) / f"day_image_{cache_token}.jpg"
    if temp_path.exists():
        return temp_path
    if cache_path is not None:
        cached = _copy_cached_variant(cache_path, temp_path)
        if cached is not None:
            return cached

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
                focus = PDF_CROP_FOCUS_FACTORS.get(normalized_focus, PDF_CROP_VERTICAL_FOCUS)
                top = max(0, int(extra_height * focus))
                box = (0, top, source_width, min(source_height, top + crop_height))

            image = image.crop(box)

            # ReportLab embeds the actual source pixels. Crop-only temp files can
            # keep multi-megapixel originals and inflate client PDFs massively.
            # Resize to roughly 2x the displayed point size, which is sharp for
            # A4 output while keeping file sizes emailable.
            target_px = (
                max(1, int(float(target_width) * 1.6)),
                max(1, int(float(target_height) * 1.6)),
            )
            if image.size != target_px:
                image = image.resize(target_px, PILImage.LANCZOS)

            image.save(temp_path, format="JPEG", quality=74, optimize=False)
            if cache_path is not None:
                try:
                    shutil.copy2(temp_path, cache_path)
                except OSError:
                    pass
            return temp_path
    except (OSError, ValueError) as error:
        diagnostics.warn_exception("pdf_image", "Could not crop image for PDF output.", error, str(source_path), source="pdf_exporter_modules.image_layout")
        return None
