"""Canonical committed day-image selection payload.

The matcher, manual override layer, preview, editor, storage and PDF paths all
exchange this versioned mapping.  Debug/provenance fields stay internal and are
never rendered as customer copy.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

SELECTION_CONTRACT_VERSION = 1


def _clean_path(value: object) -> str:
    return str(value or "").strip()


def _source_type(payload: Mapping[str, Any], *, user_override: bool) -> str:
    if user_override:
        return "manual"
    value = str(payload.get("source_type") or "").strip()
    if value:
        return value
    if payload.get("is_default") or payload.get("is_generic"):
        return "bundled_default"
    return "image_bank"


def commit_selection_payload(
    day: object,
    match: Mapping[str, Any] | None,
    *,
    user_override: bool = False,
    duplicate_policy: str = "unique",
    selection_reason: str | None = None,
) -> dict[str, Any] | None:
    """Return one immutable-by-convention, versioned selection mapping."""

    if not isinstance(match, Mapping):
        return None
    payload = dict(match)
    path = _clean_path(payload.get("path"))
    data_uri = _clean_path(payload.get("data_uri"))
    if not path and not data_uri:
        return None

    reason = str(selection_reason or payload.get("reason") or "selected image").strip()
    source_type = _source_type(payload, user_override=user_override)
    is_fallback = bool(payload.get("is_default") or payload.get("is_generic") or payload.get("fallback_reason"))
    filename = str(payload.get("filename") or (Path(path).stem if path else "preview_image"))
    score_breakdown = dict(payload.get("score_breakdown") or {}) if isinstance(payload.get("score_breakdown"), Mapping) else {}

    payload.update(
        {
            "selection_contract_version": SELECTION_CONTRACT_VERSION,
            "day": str(day or payload.get("day") or ""),
            "path": path,
            "filename": filename,
            "reason": reason,
            "source_type": source_type,
            "user_override": bool(user_override),
            "fallback_state": "fallback" if is_fallback else "matched",
            "duplicate_policy": str(duplicate_policy or "unique"),
            "candidate_provenance": {
                "path": path,
                "filename": filename,
                "city": str(payload.get("city") or ""),
                "country": str(payload.get("country") or ""),
                "source_type": source_type,
            },
            "selection_debug": {
                "selected_candidate": path or data_uri,
                "selection_reason": reason,
                "score": int(payload.get("score") or 0),
                "score_breakdown": score_breakdown,
                "fallback_state": "fallback" if is_fallback else "matched",
                "user_override": bool(user_override),
                "candidate_provenance": {
                    "path": path,
                    "filename": filename,
                    "source_type": source_type,
                },
                "duplicate_prevention_reason": str(duplicate_policy or "unique"),
            },
        }
    )
    return payload


def selection_path(match: Mapping[str, Any] | None) -> str:
    return _clean_path(match.get("path")) if isinstance(match, Mapping) else ""


__all__ = ["SELECTION_CONTRACT_VERSION", "commit_selection_payload", "selection_path"]
