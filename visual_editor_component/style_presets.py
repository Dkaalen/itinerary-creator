"""Controlled visual-editor style preset registry.

The JSON file beside this module is the source of truth for controlled editor
style ids, labels, class names, and PDF style metadata. Keep frontend/PDF tests
pointed at this registry so preview, saved HTML, and PDF export cannot drift
silently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).with_name("style_presets.json")


def _non_empty_class_names(items: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(str(item.get("class_name") or "") for item in items if item.get("class_name"))


@lru_cache(maxsize=1)
def style_preset_registry() -> dict[str, Any]:
    """Return the controlled style-preset registry."""

    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def preset_group(group_name: str) -> tuple[dict[str, Any], ...]:
    group = style_preset_registry().get(group_name, [])
    if not isinstance(group, list):
        return ()
    return tuple(item for item in group if isinstance(item, dict))


def preset_class_map(group_name: str) -> dict[str, str]:
    return {str(item.get("id")): str(item.get("class_name") or "") for item in preset_group(group_name)}


def preset_classes(group_name: str) -> tuple[str, ...]:
    return _non_empty_class_names(list(preset_group(group_name)))


def block_html(block_id: str) -> str:
    for item in preset_group("blocks"):
        if item.get("id") == block_id:
            return str(item.get("html") or "")
    return ""


def block_classes() -> tuple[str, ...]:
    return preset_classes("blocks")


def extra_allowed_classes() -> tuple[str, ...]:
    values = style_preset_registry().get("extra_allowed_classes", [])
    if not isinstance(values, list):
        return ()
    return tuple(str(value) for value in values if value)


TEXT_STYLE_CLASSES = preset_classes("text_styles")
COLOR_STYLE_CLASSES = preset_classes("colors")
SPACING_STYLE_CLASSES = preset_classes("spacing")
FONT_FAMILY_STYLE_CLASSES = preset_classes("font_families")
FONT_SIZE_STYLE_CLASSES = preset_classes("font_sizes")
BLOCK_STYLE_CLASSES = block_classes()
CONTROLLED_STYLE_CLASSES = (
    TEXT_STYLE_CLASSES
    + FONT_FAMILY_STYLE_CLASSES
    + FONT_SIZE_STYLE_CLASSES
    + COLOR_STYLE_CLASSES
    + SPACING_STYLE_CLASSES
)
ALLOWED_STYLE_CLASSES = CONTROLLED_STYLE_CLASSES + BLOCK_STYLE_CLASSES + extra_allowed_classes()


def pdf_base_style_for_classes(classes: set[str], default_style_name: str) -> str:
    for item in preset_group("text_styles"):
        class_name = str(item.get("class_name") or "")
        if class_name and class_name in classes and item.get("pdf_base_style"):
            return str(item["pdf_base_style"])
    return default_style_name


def pdf_effects_for_classes(classes: set[str]) -> list[dict[str, Any]]:
    """Return PDF color/spacing effects in registry order for CSS classes."""

    effects: list[dict[str, Any]] = []
    for group_name in ("text_styles", "font_families", "font_sizes", "colors", "spacing"):
        for item in preset_group(group_name):
            class_name = str(item.get("class_name") or "")
            if class_name and class_name in classes:
                effects.append(item)
    return effects
