"""Day-image override and crop-focus helpers.

UI helpers that intentionally create editable override slots live next to pure
read helpers used by export/PDF code.  Keeping these paths separate prevents a
PDF export from mutating Streamlit session state just because it had to read an
image crop setting.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

CROP_FOCUS_OPTIONS = {
    "Sky / upper focus": "top",
    "Center focus": "center",
    "Lower focus": "bottom",
}

CROP_FOCUS_LABELS = {value: label for label, value in CROP_FOCUS_OPTIONS.items()}

CROP_FOCUS_OBJECT_POSITIONS = {
    "top": "center 22%",
    "center": "center center",
    "bottom": "center 78%",
}

_DEFAULT_DAY_IMAGE_CHOICE = {"mode": "auto", "path": "", "crop_focus": "top"}
_REMOVED_IMAGE_MODES = {"none", "removed", "remove", "deleted", "delete"}


def normalize_image_mode(value: object, *, removed: object = False, path: object = "") -> str:
    """Return the canonical image-choice mode used by preview and PDF export.

    Older saved projects used ``mode="removed"`` and/or ``removed=True``.
    The live editor now sends ``mode="none"``.  Normalize both to one
    durable value so removed images cannot silently fall back to auto images.
    """

    if bool(removed):
        return "none"
    raw_text = "" if value is None else str(value).strip().lower()
    text = raw_text or "auto"
    if text in _REMOVED_IMAGE_MODES:
        return "none"
    if text == "manual" or (not raw_text and str(path or "").strip()):
        return "manual"
    return "auto"


def normalize_crop_focus(value: object) -> str:
    """Return the supported crop-focus token for a user/browser value."""

    value = str(value or "").strip().lower()
    if value in {"top", "upper", "sky", "aurora"}:
        return "top"
    if value in {"bottom", "lower"}:
        return "bottom"
    if value in {"center", "centre", "middle"}:
        return "center"
    return "top"


def get_day_image_overrides(output_edits: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
    """Return the mutable day-image override mapping for editor/UI writes."""

    if output_edits is None:
        output_edits = {}
    existing = output_edits.get("day_images")
    if isinstance(existing, MutableMapping):
        return existing
    day_images: dict[str, Any] = {}
    output_edits["day_images"] = day_images
    return day_images


def get_day_image_choice(output_edits: MutableMapping[str, Any], day: object) -> MutableMapping[str, Any]:
    """Return a mutable day-image choice, creating the editable slot when missing."""

    day_key = str(day or "")
    day_images = get_day_image_overrides(output_edits)
    choice = day_images.get(day_key)
    if not isinstance(choice, MutableMapping):
        choice = dict(_DEFAULT_DAY_IMAGE_CHOICE)
        day_images[day_key] = choice
    choice["mode"] = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
    if choice["mode"] == "none":
        choice["path"] = ""
    else:
        choice.setdefault("path", "")
    choice["crop_focus"] = normalize_crop_focus(choice.get("crop_focus", "top"))
    return choice


def read_day_image_choice(output_edits: Mapping[str, Any] | None, day: object) -> dict[str, Any]:
    """Return a normalized day-image choice without mutating ``output_edits``."""

    day_images = output_edits.get("day_images") if isinstance(output_edits, Mapping) else None
    raw_choice = day_images.get(str(day or "")) if isinstance(day_images, Mapping) else None
    if not isinstance(raw_choice, Mapping):
        return dict(_DEFAULT_DAY_IMAGE_CHOICE)
    choice = dict(_DEFAULT_DAY_IMAGE_CHOICE)
    choice.update(dict(raw_choice))
    choice["mode"] = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
    choice["path"] = "" if choice["mode"] == "none" else str(choice.get("path") or "")
    choice["crop_focus"] = normalize_crop_focus(choice.get("crop_focus", "top"))
    return choice


def get_day_image_crop_focus(output_edits: MutableMapping[str, Any], day: object) -> str:
    """Return crop focus for UI/editing paths that are allowed to create defaults."""

    return normalize_crop_focus(get_day_image_choice(output_edits, day).get("crop_focus", "top"))


def read_day_image_crop_focus(output_edits: Mapping[str, Any] | None, day: object) -> str:
    """Return crop focus for export/PDF reads without changing session state."""

    return normalize_crop_focus(read_day_image_choice(output_edits, day).get("crop_focus", "top"))
