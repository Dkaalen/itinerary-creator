"""Image-aware cover text contrast helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - missing Pillow falls back safely in deploys.
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None

from itinerary_generation.cover_assets import normalize_cover_crop_focus


_LIGHT_AREA_THRESHOLD = 0.48
_SAMPLE_BOX = (0.12, 0.06, 0.88, 0.42)
_TARGET_RATIO = 794 / 1123


def _stat_key(path: Path) -> tuple[str, int, int]:
    try:
        stat = path.stat()
    except OSError:
        return (str(path), 0, 0)
    return (str(path), int(stat.st_mtime_ns), int(stat.st_size))


def _srgb_to_linear(channel: int) -> float:
    value = max(0.0, min(1.0, float(channel) / 255.0))
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _relative_luminance(pixel: Iterable[int]) -> float:
    red, green, blue = list(pixel)[:3]
    return (
        0.2126 * _srgb_to_linear(red)
        + 0.7152 * _srgb_to_linear(green)
        + 0.0722 * _srgb_to_linear(blue)
    )


def _cover_crop_box(width: int, height: int, crop_focus: str) -> tuple[int, int, int, int]:
    source_ratio = float(width) / float(height)
    if source_ratio > _TARGET_RATIO:
        crop_width = max(1, int(height * _TARGET_RATIO))
        left = max(0, int((width - crop_width) / 2))
        return (left, 0, min(width, left + crop_width), height)

    crop_height = max(1, int(width / _TARGET_RATIO))
    extra_height = max(0, height - crop_height)
    focus = {"top": 0.0, "center": 0.5, "bottom": 1.0}.get(normalize_cover_crop_focus(crop_focus), 0.0)
    top = max(0, int(extra_height * focus))
    return (0, top, width, min(height, top + crop_height))


@lru_cache(maxsize=128)
def _cover_text_luminance_cached(path_text: str, mtime_ns: int, size: int, crop_focus: str) -> float | None:
    if Image is None or ImageOps is None:
        return None
    path = Path(path_text)
    if not path.is_file() or size <= 0:
        return None
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
            if width <= 0 or height <= 0:
                return None
            image = image.crop(_cover_crop_box(width, height, crop_focus))
            crop_width, crop_height = image.size
            left = int(crop_width * _SAMPLE_BOX[0])
            top = int(crop_height * _SAMPLE_BOX[1])
            right = max(left + 1, int(crop_width * _SAMPLE_BOX[2]))
            bottom = max(top + 1, int(crop_height * _SAMPLE_BOX[3]))
            sample = image.crop((left, top, min(crop_width, right), min(crop_height, bottom)))
            sample.thumbnail((72, 72))
            pixel_source = getattr(sample, "get_flattened_data", None)
            pixels = list(pixel_source() if callable(pixel_source) else sample.getdata())
            if not pixels:
                return None
            return sum(_relative_luminance(pixel) for pixel in pixels) / len(pixels)
    except (OSError, ValueError):
        return None


def cover_text_area_is_dark(path: str | Path | None, crop_focus: str = "top") -> bool | None:
    """Return whether the cover's text area is dark enough for light text.

    The sampled area mirrors the upper, centred cover-copy block used by both
    the browser preview and the typed PDF renderer.  ``None`` means the image
    could not be inspected and the caller should use its existing fallback.
    """

    if not path:
        return None
    image_path = Path(path)
    key_path, mtime_ns, size = _stat_key(image_path)
    luminance = _cover_text_luminance_cached(key_path, mtime_ns, size, normalize_cover_crop_focus(crop_focus))
    if luminance is None:
        return None
    return luminance < _LIGHT_AREA_THRESHOLD
