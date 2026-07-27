"""Deterministic committed-selection lifecycle for day images."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
import hashlib
import json
from typing import Any

from images.image_overrides import normalize_crop_focus, normalize_image_mode
from images.selection_contract import SELECTION_CONTRACT_VERSION, commit_selection_payload

SELECTION_COMMIT_KEY = "image_selection_commit"
SELECTION_COMMIT_VERSION = 1
_RELEVANT_ROW_FIELDS = (
    "day", "type", "effective_type", "city", "country", "title", "details",
    "description", "start_date", "end_date", "product_kind", "route_start", "route_end",
)


def _rows_signature(grouped_days: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for day, rows in (grouped_days or {}).items():
        result.append(
            {
                "day": str(day),
                "rows": [
                    {field: row.get(field) for field in _RELEVANT_ROW_FIELDS if row.get(field) not in (None, "")}
                    for row in (rows or [])
                    if isinstance(row, Mapping)
                ],
            }
        )
    return result


def _override_signature(output_edits: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
    edits = output_edits if isinstance(output_edits, Mapping) else {}
    raw = edits.get("day_images") if isinstance(edits.get("day_images"), Mapping) else {}
    result: dict[str, dict[str, str]] = {}
    for day, choice in raw.items():
        if not isinstance(choice, Mapping):
            continue
        mode = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
        result[str(day)] = {
            "mode": mode,
            "path": "" if mode == "none" else str(choice.get("path") or ""),
            "crop_focus": normalize_crop_focus(choice.get("crop_focus") or "top"),
        }
    return result


def selection_input_signature(
    grouped_days: Mapping[str, Any] | None,
    output_edits: Mapping[str, Any] | None,
    *,
    image_bank_signature: str,
    default_images_allowed: bool,
) -> str:
    payload = {
        "contract_version": SELECTION_CONTRACT_VERSION,
        "rows": _rows_signature(grouped_days),
        "overrides": _override_signature(output_edits),
        "image_bank_signature": str(image_bank_signature or ""),
        "default_images_allowed": bool(default_images_allowed),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_selection_commit(output_edits: Mapping[str, Any] | None, *, expected_signature: str) -> dict[str, Any] | None:
    edits = output_edits if isinstance(output_edits, Mapping) else {}
    commit = edits.get(SELECTION_COMMIT_KEY)
    if not isinstance(commit, Mapping):
        return None
    if int(commit.get("version") or 0) != SELECTION_COMMIT_VERSION:
        return None
    if str(commit.get("input_signature") or "") != str(expected_signature):
        return None
    raw_matches = commit.get("matches")
    if not isinstance(raw_matches, Mapping):
        return None
    matches: dict[str, Any] = {}
    for day, match in raw_matches.items():
        if match is None:
            matches[str(day)] = None
            continue
        committed = commit_selection_payload(str(day), match, user_override=bool(match.get("user_override")), duplicate_policy=str(match.get("duplicate_policy") or "unique")) if isinstance(match, Mapping) else None
        if committed is None:
            return None
        matches[str(day)] = committed
    return deepcopy(matches)


def store_selection_commit(output_edits: Mapping[str, Any] | None, *, input_signature: str, matches: Mapping[str, Any]) -> None:
    if not isinstance(output_edits, MutableMapping):
        return
    output_edits[SELECTION_COMMIT_KEY] = {
        "version": SELECTION_COMMIT_VERSION,
        "input_signature": str(input_signature),
        "matches": deepcopy(dict(matches or {})),
    }


__all__ = [
    "SELECTION_COMMIT_KEY",
    "SELECTION_COMMIT_VERSION",
    "read_selection_commit",
    "selection_input_signature",
    "store_selection_commit",
]
