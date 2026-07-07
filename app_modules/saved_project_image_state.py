"""Compact saved-project image-state helpers."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


from app_modules.saved_project_model import SavedProjectImageState
from ui.picture_workflow import PICTURES_ADDED_KEY


def image_state_from_output_edits(output_edits: Mapping[str, Any]) -> SavedProjectImageState:
    """Extract durable image edits from output edits without preview payloads."""

    return SavedProjectImageState(
        cover_image=_image_choice(output_edits.get("cover_image") or {}),
        summary_image=_image_choice(output_edits.get("summary_image") or {}),
        day_images=_day_image_choices(output_edits.get("day_images") or {}),
        pictures_added=bool(output_edits.get(PICTURES_ADDED_KEY)),
    )


def apply_image_state_to_output_edits(
    output_edits: Mapping[str, Any],
    image_state: SavedProjectImageState,
) -> dict[str, Any]:
    """Return output edits with saved image choices restored."""

    restored = deepcopy(dict(output_edits or {}))
    if image_state.cover_image:
        restored["cover_image"] = _image_choice(image_state.cover_image)
    if image_state.summary_image:
        restored["summary_image"] = _image_choice(image_state.summary_image)
    if image_state.day_images:
        restored["day_images"] = _day_image_choices(image_state.day_images)
    restored[PICTURES_ADDED_KEY] = bool(image_state.pictures_added or restored.get(PICTURES_ADDED_KEY))
    return restored


def _image_choice(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    choice = deepcopy(dict(value))
    if choice:
        mode = str(choice.get("mode") or "auto").strip().lower()
        removed = bool(choice.get("removed", False)) or mode in {"removed", "remove", "deleted", "delete"}
        if removed or mode == "none":
            choice["mode"] = "none"
            choice["path"] = ""
            if removed:
                choice["removed"] = True
        elif mode == "manual" or (mode in {"", "auto"} and str(choice.get("path") or "").strip()):
            choice["mode"] = "manual"
            choice["path"] = str(choice.get("path") or "").strip()
        else:
            choice["mode"] = "auto"
            choice["path"] = ""
        choice["crop_focus"] = str(choice.get("crop_focus") or "top")
    return choice


def _day_image_choices(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    return {str(day): _image_choice(choice) for day, choice in value.items() if isinstance(choice, Mapping)}
