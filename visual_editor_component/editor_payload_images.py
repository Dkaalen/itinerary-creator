"""Image payload helpers for the visual editor."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from images.app_image_selection import (
    audit_day_image_matches,
    get_image_bank_scan_paths,
    get_image_preview_for_path,
    list_replacement_image_options_for_rows,
    normalize_crop_focus,
    select_day_images_with_overrides,
)
from images.scanner import get_image_bank_index
from itinerary_generation.cover_assets import resolve_cover_background


DAY_REPLACEMENT_OPTION_LIMIT = 8
OPTION_PREVIEW_LIMIT = DAY_REPLACEMENT_OPTION_LIMIT
EDITOR_IMAGE_PAYLOAD_CACHE_LIMIT = 18

_IMAGE_PAYLOAD_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default, separators=(",", ":"))


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8", errors="ignore")).hexdigest()[:24]


def _row_image_signature(row: Mapping[str, Any] | Any, index: int) -> dict[str, str]:
    if not isinstance(row, Mapping):
        return {"index": str(index), "value": str(row)}
    return {
        "row_id": str(row.get("row_id") or row.get("line_number") or index),
        "day": str(row.get("day") or ""),
        "date": str(row.get("date") or row.get("start_date") or ""),
        "type": str(row.get("effective_type") or row.get("type") or ""),
        "city": str(row.get("city") or row.get("destination") or ""),
        "title": str(row.get("title") or row.get("original_title") or row.get("hotel_name") or ""),
        "details": str(row.get("details") or row.get("description") or ""),
        "raw_text": str(row.get("raw_text") or ""),
        "client_description": str(row.get("client_description") or ""),
        "month": str(row.get("month") or ""),
    }


def _grouped_days_image_signature(grouped_days) -> str:
    pieces = []
    for day, rows in (grouped_days or {}).items():
        pieces.append({
            "day": str(day),
            "rows": [_row_image_signature(row, index) for index, row in enumerate(rows or [])],
        })
    return _hash_payload(pieces)


def _parsed_rows_image_signature(parsed_rows) -> str:
    return _hash_payload([_row_image_signature(row, index) for index, row in enumerate(parsed_rows or [])])


def _relevant_image_edits(output_edits: Mapping[str, Any] | Any) -> dict[str, Any]:
    edits = output_edits if isinstance(output_edits, Mapping) else {}
    return {
        "day_images": deepcopy(edits.get("day_images") if isinstance(edits.get("day_images"), Mapping) else {}),
        "cover_image": deepcopy(edits.get("cover_image") if isinstance(edits.get("cover_image"), Mapping) else {}),
        "summary_image": deepcopy(edits.get("summary_image") if isinstance(edits.get("summary_image"), Mapping) else {}),
        "cover_season": str(edits.get("cover_season") or ""),
        "detected_cover_season": str(edits.get("detected_cover_season") or ""),
        "output_brand": str(edits.get("output_brand") or ""),
        "color_preset": str(edits.get("color_preset") or ""),
        "block_default_final_images": bool(edits.get("block_default_final_images")),
    }


def _image_bank_signature(*, pictures_added: bool) -> str:
    if not pictures_added:
        return "pictures-pending"
    try:
        index = get_image_bank_index(get_image_bank_scan_paths())
        return repr(index.cache_key)
    except (OSError, TypeError, ValueError) as error:
        # Keep the editor usable if the image bank cannot be inspected.  The
        # expensive helpers will still surface normal image-bank warnings.
        return f"image-bank-error:{type(error).__name__}:{error}"


def _editor_image_payload_cache_key(parsed_rows, grouped_days, output_edits, *, pictures_added: bool) -> str:
    payload = {
        "version": 1,
        "pictures_added": bool(pictures_added),
        "parsed_rows": _parsed_rows_image_signature(parsed_rows),
        "grouped_days": _grouped_days_image_signature(grouped_days),
        "image_edits": _relevant_image_edits(output_edits),
        "image_bank": _image_bank_signature(pictures_added=pictures_added),
    }
    return _hash_payload(payload)


def clear_editor_image_payload_cache() -> None:
    """Clear the process-local visual-editor image payload cache."""

    _IMAGE_PAYLOAD_CACHE.clear()


def editor_image_payload_cache_info() -> dict[str, int]:
    """Return lightweight cache diagnostics for tests and debug-only callers."""

    return {"size": len(_IMAGE_PAYLOAD_CACHE), "limit": EDITOR_IMAGE_PAYLOAD_CACHE_LIMIT}


def _cache_get(key: str) -> dict[str, Any] | None:
    cached = _IMAGE_PAYLOAD_CACHE.get(key)
    if cached is None:
        return None
    _IMAGE_PAYLOAD_CACHE.move_to_end(key)
    return deepcopy(cached)


def _cache_set(key: str, value: dict[str, Any]) -> dict[str, Any]:
    _IMAGE_PAYLOAD_CACHE[key] = deepcopy(value)
    _IMAGE_PAYLOAD_CACHE.move_to_end(key)
    while len(_IMAGE_PAYLOAD_CACHE) > EDITOR_IMAGE_PAYLOAD_CACHE_LIMIT:
        _IMAGE_PAYLOAD_CACHE.popitem(last=False)
    return deepcopy(value)


def _with_option_previews(options, *, preview_limit: int = OPTION_PREVIEW_LIMIT):
    enriched = []
    for index, option in enumerate(options or []):
        item = dict(option or {})
        path = item.get("path")
        if path and not item.get("preview_data_uri") and index < preview_limit:
            item["preview_data_uri"] = get_image_preview_for_path(path, option=True)
        else:
            item.setdefault("preview_data_uri", "")
        enriched.append(item)
    return enriched


def _editor_cover_image_payload(parsed_rows, output_edits, key: str, *, pictures_added: bool) -> dict:
    image = resolve_cover_background(parsed_rows, output_edits, key=key, include_image_data=False)
    if not pictures_added:
        image["data_uri"] = ""
        image["auto_data_uri"] = ""
        return image
    if image.get("path"):
        image["data_uri"] = get_image_preview_for_path(image.get("path"))
    if image.get("auto_path"):
        image["auto_data_uri"] = get_image_preview_for_path(image.get("auto_path"))
    image["options"] = _with_option_previews(image.get("options") or [])
    return image


def _build_day_image_context_uncached(grouped_days, output_edits, *, pictures_added: bool):
    image_matches = select_day_images_with_overrides(grouped_days, output_edits) if pictures_added else {}
    image_warnings = audit_day_image_matches(grouped_days, image_matches, output_edits) if pictures_added else ()
    image_warnings_by_day = {}
    for warning in image_warnings:
        image_warnings_by_day.setdefault(warning.day, []).append({
            "code": warning.code,
            "severity": warning.severity,
            "message": warning.message,
            "path": warning.path,
        })
    return image_matches, image_warnings, image_warnings_by_day


def build_day_image_context(grouped_days, output_edits, *, pictures_added: bool):
    key = _editor_image_payload_cache_key([], grouped_days, output_edits, pictures_added=pictures_added)
    cached = _cache_get(f"context:{key}")
    if cached is not None:
        return cached["image_matches"], cached["image_warnings"], cached["image_warnings_by_day"]
    image_matches, image_warnings, image_warnings_by_day = _build_day_image_context_uncached(
        grouped_days,
        output_edits,
        pictures_added=pictures_added,
    )
    bundle = {
        "image_matches": image_matches,
        "image_warnings": image_warnings,
        "image_warnings_by_day": image_warnings_by_day,
    }
    cached_bundle = _cache_set(f"context:{key}", bundle)
    return cached_bundle["image_matches"], cached_bundle["image_warnings"], cached_bundle["image_warnings_by_day"]


def _day_image_choice_for_payload(output_edits: Mapping[str, Any] | Any, day: str) -> dict[str, str]:
    edits = output_edits if isinstance(output_edits, Mapping) else {}
    day_images = edits.get("day_images") if isinstance(edits.get("day_images"), Mapping) else {}
    raw = day_images.get(day) if isinstance(day_images.get(day), Mapping) else {}
    mode = str(raw.get("mode") or "auto").strip().lower()
    if mode not in {"auto", "manual", "none"}:
        mode = "auto"
    return {
        "mode": mode,
        "path": str(raw.get("path") or ""),
        "crop_focus": normalize_crop_focus(raw.get("crop_focus") or "top"),
    }


def _build_day_image_payload_uncached(day, rows, output_edits, *, pictures_added: bool, image_matches, image_warnings_by_day):
    if pictures_added:
        match = image_matches.get(day)
        image_path = match.get("path") if match else ""
        preview_data_uri = get_image_preview_for_path(image_path) if image_path else ""
        options = _with_option_previews(list_replacement_image_options_for_rows(day, rows, limit=DAY_REPLACEMENT_OPTION_LIMIT))
        choice = _day_image_choice_for_payload(output_edits, day)
        return {
            "mode": choice.get("mode", "auto"),
            "path": image_path or "",
            "name": Path(image_path).name if image_path else "",
            "data_uri": preview_data_uri,
            "auto_path": image_path or "",
            "auto_name": Path(image_path).name if image_path else "",
            "auto_data_uri": preview_data_uri,
            "crop_focus": choice.get("crop_focus", "top"),
            "options": options,
            "warnings": image_warnings_by_day.get(day, []),
        }
    return {
        "mode": "pending",
        "path": "",
        "name": "",
        "data_uri": "",
        "auto_path": "",
        "auto_name": "",
        "auto_data_uri": "",
        "crop_focus": "top",
        "options": [],
        "pictures_pending": True,
        "warnings": [],
    }


def build_day_image_payload(day, rows, output_edits, *, pictures_added: bool, image_matches, image_warnings_by_day):
    key = _hash_payload({
        "version": 1,
        "day": str(day),
        "rows": [_row_image_signature(row, index) for index, row in enumerate(rows or [])],
        "image_edits": _relevant_image_edits(output_edits),
        "match": image_matches.get(day) if isinstance(image_matches, Mapping) else None,
        "warnings": image_warnings_by_day.get(day, []) if isinstance(image_warnings_by_day, Mapping) else [],
        "image_bank": _image_bank_signature(pictures_added=pictures_added),
        "pictures_added": bool(pictures_added),
    })
    cached = _cache_get(f"day:{key}")
    if cached is not None:
        return cached
    return _cache_set(
        f"day:{key}",
        _build_day_image_payload_uncached(
            day,
            rows,
            output_edits,
            pictures_added=pictures_added,
            image_matches=image_matches,
            image_warnings_by_day=image_warnings_by_day,
        ),
    )


def build_cover_image_payloads(parsed_rows, output_edits, *, pictures_added: bool):
    key = _hash_payload({
        "version": 1,
        "parsed_rows": _parsed_rows_image_signature(parsed_rows),
        "image_edits": _relevant_image_edits(output_edits),
        "image_bank": _image_bank_signature(pictures_added=pictures_added),
        "pictures_added": bool(pictures_added),
    })
    cached = _cache_get(f"cover:{key}")
    if cached is not None:
        return cached["cover_image"], cached["summary_image"]
    cover_image = _editor_cover_image_payload(parsed_rows, output_edits, "cover_image", pictures_added=pictures_added)
    summary_image = _editor_cover_image_payload(parsed_rows, output_edits, "summary_image", pictures_added=pictures_added)
    cached_bundle = _cache_set(f"cover:{key}", {"cover_image": cover_image, "summary_image": summary_image})
    return cached_bundle["cover_image"], cached_bundle["summary_image"]


def build_editor_image_payload_bundle(parsed_rows, grouped_days, output_edits, *, pictures_added: bool) -> dict[str, Any]:
    """Return all visual-editor image payload pieces through one stable cache.

    The editor reruns frequently while text fields, inspector panels and
    workflow controls update.  Image matching, replacement-option ranking and
    preview data-URI creation are much heavier than those reruns.  This bundle
    caches the complete image-facing payload by the source/render signature,
    image edits, selected brand/theme and image-bank fingerprint so normal
    reruns reuse the last payload while removals/replacements/crop changes still
    invalidate immediately.
    """

    key = _editor_image_payload_cache_key(parsed_rows, grouped_days, output_edits, pictures_added=pictures_added)
    cached = _cache_get(f"bundle:{key}")
    if cached is not None:
        return cached

    image_matches, image_warnings, image_warnings_by_day = _build_day_image_context_uncached(
        grouped_days,
        output_edits,
        pictures_added=pictures_added,
    )
    day_images = {
        day: _build_day_image_payload_uncached(
            day,
            rows,
            output_edits,
            pictures_added=pictures_added,
            image_matches=image_matches,
            image_warnings_by_day=image_warnings_by_day,
        )
        for day, rows in (grouped_days or {}).items()
    }
    cover_image = _editor_cover_image_payload(parsed_rows, output_edits, "cover_image", pictures_added=pictures_added)
    summary_image = _editor_cover_image_payload(parsed_rows, output_edits, "summary_image", pictures_added=pictures_added)
    return _cache_set(
        f"bundle:{key}",
        {
            "image_matches": image_matches,
            "image_warnings": image_warnings,
            "image_warnings_by_day": image_warnings_by_day,
            "day_images": day_images,
            "cover_image": cover_image,
            "summary_image": summary_image,
        },
    )
