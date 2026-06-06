"""Browser-friendly image preview helpers."""

from pathlib import Path
from functools import lru_cache
import base64
import mimetypes

import diagnostics


def image_to_data_uri(path):
    raw_path = path
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except (OSError, TypeError, ValueError) as error:
        diagnostics.warn_exception("image_preview", "Could not encode image preview.", error, str(raw_path), source="images.image_preview")
        return ""


@lru_cache(maxsize=256)
def _image_to_preview_data_uri_cached(path_text, max_size, quality, mtime):
    try:
        from io import BytesIO
        from PIL import Image

        path = Path(path_text)
        if not path.exists() or not path.is_file():
            return ""
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except (OSError, TypeError, ValueError) as error:
        diagnostics.warn_exception("image_preview", "Could not build resized image preview.", error, str(path_text), source="images.image_preview")
        return ""


def image_to_preview_data_uri(path, max_size=(560, 380), quality=48):
    """Return a browser-friendly preview data URI instead of the original image.

    The visual editor only needs a screen preview. Sending original local image
    files through Streamlit can create enormous component payloads when the
    image bank contains high-resolution photos. This helper keeps the editor
    responsive while the PDF exporter continues to use the original file path.
    """
    raw_path = path
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        cached = _image_to_preview_data_uri_cached(str(path.resolve()), tuple(max_size), int(quality), path.stat().st_mtime)
        if cached:
            return cached
    except (OSError, TypeError, ValueError) as error:
        diagnostics.warn_exception("image_preview", "Could not read image preview metadata.", error, str(raw_path), source="images.image_preview")

    # Fall back only for very small files. Large originals are exactly what
    # caused Streamlit message-size failures, so never blindly encode them.
    try:
        path = Path(raw_path)
        if path.exists() and path.stat().st_size <= 350_000:
            return image_to_data_uri(path)
    except (OSError, TypeError, ValueError) as error:
        diagnostics.warn_exception("image_preview", "Could not use small original image preview fallback.", error, str(raw_path), source="images.image_preview")
    return ""


def image_to_option_preview_data_uri(path):
    """Return a tiny preview used only after choosing a replacement image."""
    return image_to_preview_data_uri(path, max_size=(240, 170), quality=42)


def get_image_preview_for_path(path, option=False):
    if not path:
        return ""
    return image_to_option_preview_data_uri(path) if option else image_to_preview_data_uri(path)
