"""Metadata-first replacement image option payloads for the visual editor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

_HEAVY_IMAGE_FIELDS = frozenset(
    {
        "data_uri",
        "preview_data_uri",
        "thumbnail_data_uri",
        "thumbnail",
        "thumb_data_uri",
        "base64",
        "image_data",
    }
)


def metadata_first_image_option(option: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Return one replacement option without eager image bytes."""

    raw = option if isinstance(option, Mapping) else {}
    path = str(raw.get("path") or "")
    name = str(raw.get("name") or raw.get("label") or (Path(path).name if path else ""))
    clean: dict[str, Any] = {
        "path": path,
        "name": name,
        "label": str(raw.get("label") or name),
        "season": str(raw.get("season") or ""),
        "city": str(raw.get("city") or raw.get("destination") or ""),
    }
    for key in ("score", "source", "folder", "reason"):
        if key in raw and key not in _HEAVY_IMAGE_FIELDS:
            clean[key] = raw.get(key)
    return {key: value for key, value in clean.items() if value not in (None, "")}


def metadata_first_image_options(options: Any, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Return replacement options safe to include in frequent editor payloads."""

    values = list(options or [])
    if limit is not None:
        values = values[: max(0, int(limit))]
    return [metadata_first_image_option(option) for option in values]


def option_payload_has_eager_image_data(option: Mapping[str, Any]) -> bool:
    """Return whether a replacement option still carries eager image bytes."""

    return any(bool(option.get(key)) for key in _HEAVY_IMAGE_FIELDS)


__all__ = [
    "metadata_first_image_option",
    "metadata_first_image_options",
    "option_payload_has_eager_image_data",
]
