"""Persistent visual-editor draft autosave helpers.

These helpers intentionally store only the current editable project state that
already exists in memory.  They do not regenerate itineraries, fetch images, or
perform any expensive work.  The running app can use the JSON files to recover a
preview/editing session after a browser refresh, dropped connection, or crash.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DRAFT_SCHEMA_VERSION = 1
DEFAULT_DRAFT_DIR = "persistent_drafts"
_MAX_AUTOSAVE_BYTES = 2_500_000


@dataclass(frozen=True)
class DraftAutosaveRecord:
    schema_version: int
    saved_at: str
    draft_id: str
    source_signature: str
    payload_hash: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "saved_at": self.saved_at,
            "draft_id": self.draft_id,
            "source_signature": self.source_signature,
            "payload_hash": self.payload_hash,
            "payload": self.payload,
        }


def draft_autosave_dir() -> Path:
    return Path(os.environ.get("ITINERARY_DRAFT_AUTOSAVE_DIR", DEFAULT_DRAFT_DIR)).expanduser()


def _clean_id(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip(".-_")
    return text[:120] or "draft"


def draft_path(draft_id: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir is not None else draft_autosave_dir()
    return root / f"{_clean_id(draft_id)}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_for_hash(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_json_for_hash(payload).encode("utf-8", errors="ignore")).hexdigest()[:24]


def _source_signature_from_payload(payload: Mapping[str, Any]) -> str:
    meta = payload.get("meta") if isinstance(payload.get("meta"), Mapping) else {}
    return str(meta.get("source_signature") or "").strip()


def _draft_id_from_payload(payload: Mapping[str, Any], fallback: str = "") -> str:
    return str(payload.get("draft_id") or fallback or "draft").strip()


def _compact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a storage-safe copy of the editor payload.

    The visual editor already removes large preview data before committing most
    payloads, but this extra guard keeps autosaves small if a browser sends an
    older/full payload shape.
    """
    data = json.loads(json.dumps(payload or {}, ensure_ascii=False, default=str))
    for day in data.get("days") or []:
        if not isinstance(day, dict):
            continue
        image = day.get("image") if isinstance(day.get("image"), dict) else None
        if not image:
            continue
        image.pop("data_uri", None)
        image.pop("auto_data_uri", None)
        image.pop("options", None)
        upload = image.get("upload") if isinstance(image.get("upload"), dict) else None
        if upload and upload.get("data_uri"):
            # Manual uploaded images are needed for real recovery, so keep them.
            # The size guard below protects server storage from extreme cases.
            pass
    return data


def make_autosave_record(payload: Mapping[str, Any], *, draft_id: str | None = None) -> DraftAutosaveRecord:
    compact = _compact_payload(payload)
    resolved_draft_id = _draft_id_from_payload(compact, fallback=draft_id or "")
    return DraftAutosaveRecord(
        schema_version=DRAFT_SCHEMA_VERSION,
        saved_at=_now_iso(),
        draft_id=resolved_draft_id,
        source_signature=_source_signature_from_payload(compact),
        payload_hash=payload_hash(compact),
        payload=compact,
    )


def save_autosave_payload(
    payload: Mapping[str, Any],
    *,
    draft_id: str | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    record = make_autosave_record(payload, draft_id=draft_id)
    serialized = json.dumps(record.as_dict(), ensure_ascii=False, indent=2, default=str)
    if len(serialized.encode("utf-8")) > _MAX_AUTOSAVE_BYTES:
        return {
            "ok": False,
            "reason": "autosave_too_large",
            "draft_id": record.draft_id,
            "saved_at": record.saved_at,
            "payload_hash": record.payload_hash,
        }
    path = draft_path(record.draft_id, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(serialized, encoding="utf-8")
    tmp.replace(path)
    return {
        "ok": True,
        "path": str(path),
        "draft_id": record.draft_id,
        "saved_at": record.saved_at,
        "payload_hash": record.payload_hash,
    }


def load_autosave_payload(
    draft_id: str,
    *,
    source_signature: str = "",
    base_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    path = draft_path(draft_id, base_dir=base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    payload = data.get("payload")
    if not isinstance(payload, dict):
        return None
    saved_signature = str(data.get("source_signature") or payload.get("meta", {}).get("source_signature") or "")
    if source_signature and saved_signature and saved_signature != source_signature:
        return None
    return payload


def delete_autosave(draft_id: str, *, base_dir: str | Path | None = None) -> bool:
    path = draft_path(draft_id, base_dir=base_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def apply_autosaved_payload_to_output_edits(
    payload: Mapping[str, Any],
    output_edits: dict[str, Any],
    apply_func,
) -> bool:
    """Apply a saved visual-editor payload using the normal editor-save path."""
    if not isinstance(payload, Mapping) or not isinstance(output_edits, dict):
        return False
    return bool(apply_func(json.dumps(payload, ensure_ascii=False, default=str), output_edits))
