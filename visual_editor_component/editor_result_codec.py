"""Decode visual-editor result payloads and compare edit snapshots."""

import json


def _normalize_route_edit(value):
    """Normalize editable cover-route text back to a single separator-delimited line."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", " · ")
    parts = [part.strip() for part in text.split("·") if part.strip()]
    return " · ".join(parts)


def _decode_visual_editor_result(result):
    """Decode visual editor payloads, including export/autosave wrappers."""
    data = json.loads(result) if isinstance(result, str) else result
    if isinstance(data, dict) and "payload" in data and ("commit_nonce" in data or "autosave" in data):
        commit_nonce = str(data.get("commit_nonce") or "")
        return data.get("payload") or {}, commit_nonce, bool(data.get("autosave"))
    return data, "", False


def _stable_output_edits_snapshot(output_edits):
    return json.dumps(output_edits or {}, ensure_ascii=False, sort_keys=True, default=str)
