"""Day image matching and override selection helpers."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

from images.matcher import select_day_images
from images.scanner import get_image_bank_index
from images.selection_commit import read_selection_commit, selection_input_signature, store_selection_commit
from images.selection_contract import commit_selection_payload
from images.image_bank import image_bank_status_for_paths, normalize_path_key
from images.image_overrides import normalize_image_mode


def day_image_match_from_path(day, path, reason="manual selection", image_bank_status=None):
    if not path:
        return None
    path_obj = Path(path)
    payload = {
        "day": day,
        "path": str(path_obj),
        "score": 999,
        "reason": reason,
        "city": "",
        "country": "",
        "filename": path_obj.stem,
        "themes": [],
        "seasons": [],
        "is_default": False,
        "is_generic": False,
        "fallback_reason": "",
        "image_bank_status": dict(image_bank_status or {}),
        "source_type": "manual",
        "score_breakdown": {
            "destination_score": 0,
            "activity_product_score": 0,
            "season_score": 0,
            "country_region_score": 0,
            "fallback_score": 0,
            "total_score": 999,
        },
    }
    return commit_selection_payload(day, payload, user_override=True, selection_reason=reason)


def normalize_day_image_match(day, match, *, image_bank_status=None):
    """Return the canonical day-image match payload or ``None``.

    Older saved projects/tests may store ``day_image_matches`` as a plain image
    path string. Newer code expects a structured mapping with a ``path`` key.
    Normalizing at the boundary keeps workflow, preview, audit and PDF code from
    each carrying their own compatibility checks.
    """

    if not match:
        return None
    if isinstance(match, Mapping):
        path = str(match.get("path", "") or "").strip()
        if not path and not match.get("data_uri"):
            return None
        payload = dict(match)
        payload.setdefault("day", day)
        if image_bank_status is not None and not isinstance(payload.get("image_bank_status"), Mapping):
            payload["image_bank_status"] = dict(image_bank_status or {})
        return commit_selection_payload(
            day,
            payload,
            user_override=bool(payload.get("user_override")),
            duplicate_policy=str(payload.get("duplicate_policy") or "unique"),
        )
    path = str(match or "").strip()
    if not path:
        return None
    return day_image_match_from_path(day, path, reason="legacy image match path", image_bank_status=image_bank_status)


def normalize_day_image_matches(matches, *, image_bank_status=None):
    """Normalize a mapping of day -> image match payloads.

    Explicit empty/removed days are preserved as ``None`` so downstream code can
    distinguish an intentional no-image state from an absent match mapping.
    """

    normalized = {}
    for day, match in (matches or {}).items():
        normalized[str(day)] = normalize_day_image_match(str(day), match, image_bank_status=image_bank_status)
    return normalized


def _attach_image_bank_contract(match, status):
    if not match:
        return match
    payload = dict(match)
    payload["image_bank_status"] = dict(status or {})
    if payload.get("is_default") or payload.get("is_generic"):
        payload.setdefault("source_type", "bundled_default")
    elif status.get("full_bank_found"):
        payload.setdefault("source_type", "full_bank")
    else:
        payload.setdefault("source_type", "unknown")
    return payload


def _default_images_allowed_for_final(output_edits=None) -> bool:
    """Return whether bundled fallback images may be used in normal output.

    The old opt-in flag is retained for compatibility, but default images are
    now allowed unless a caller explicitly sets ``block_default_final_images``.
    """

    return not bool((output_edits or {}).get("block_default_final_images"))


def select_day_images_with_overrides(grouped_days, output_edits=None, *, app_root, image_bank_scan_paths):
    """Resolve one committed selection per day while preserving manual intent."""

    if output_edits is None:
        output_edits = {}
    overrides = output_edits.get("day_images", {}) or {}
    bank_status = image_bank_status_for_paths(image_bank_scan_paths)
    default_allowed = _default_images_allowed_for_final(output_edits)
    default_locked = bank_status.get("missing_full_bank") and not default_allowed
    bank_signature = get_image_bank_index(image_bank_scan_paths).cache_key
    input_signature = selection_input_signature(
        grouped_days,
        output_edits,
        image_bank_signature=bank_signature,
        default_images_allowed=default_allowed,
    )
    committed = read_selection_commit(output_edits, expected_signature=input_signature)
    if committed is not None:
        return committed

    selected = {}
    used_paths = set()

    # Deliberate manual reuse is authoritative.  It is recorded explicitly
    # instead of being discarded by automatic duplicate prevention.
    for day, rows in (grouped_days or {}).items():
        choice = overrides.get(day, {}) or {}
        mode = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
        manual_path = choice.get("path", "")

        if mode == "none":
            selected[day] = None
            continue

        if mode == "manual" and manual_path:
            resolved = Path(manual_path)
            if not resolved.is_absolute():
                resolved = (app_root / resolved).resolve()
            key = normalize_path_key(resolved)
            if resolved.exists():
                duplicate_policy = "intentional_manual_reuse" if key in used_paths else "unique"
                selected[day] = commit_selection_payload(
                    day,
                    day_image_match_from_path(day, resolved, reason="manual image selection", image_bank_status=bank_status),
                    user_override=True,
                    duplicate_policy=duplicate_policy,
                    selection_reason="manual image selection",
                )
                used_paths.add(key)
            else:
                selected[day] = None

    base_matches = {day: None for day in (grouped_days or {})} if default_locked else select_day_images(grouped_days, image_bank_scan_paths, used_paths=used_paths.copy())

    for day, rows in (grouped_days or {}).items():
        if day in selected:
            continue
        match = base_matches.get(day)
        duplicate_policy = "unique"
        if match:
            key = normalize_path_key(match.get("path", ""))
            allows_reuse = "reused strong default" in str(match.get("reason", "")).lower()
            if key in used_paths and not allows_reuse:
                match = None
            else:
                if key in used_paths and allows_reuse:
                    duplicate_policy = "safe_default_reuse"
                used_paths.add(key)
        match = _attach_image_bank_contract(match, bank_status)
        selected[day] = commit_selection_payload(
            day,
            match,
            duplicate_policy=duplicate_policy,
        ) if match else None

    store_selection_commit(output_edits, input_signature=input_signature, matches=selected)
    return selected

