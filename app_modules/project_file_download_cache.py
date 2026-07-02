"""Session-local saved-project download payload cache."""

from __future__ import annotations

from typing import Any, MutableMapping

PROJECT_FILE_DOWNLOAD_CACHE_KEY = "_project_file_download_cache"


def clear_project_file_download_cache(state: MutableMapping[str, Any]) -> None:
    state.pop(PROJECT_FILE_DOWNLOAD_CACHE_KEY, None)


def cached_project_file_payload(state: MutableMapping[str, Any], signature: str, builder):
    """Return cached project-file bytes for a stable current-project signature."""

    cache = state.get(PROJECT_FILE_DOWNLOAD_CACHE_KEY)
    if isinstance(cache, dict) and cache.get("signature") == signature:
        return cache.get("payload")
    payload = builder()
    state[PROJECT_FILE_DOWNLOAD_CACHE_KEY] = {"signature": signature, "payload": payload}
    return payload


__all__ = [
    "PROJECT_FILE_DOWNLOAD_CACHE_KEY",
    "cached_project_file_payload",
    "clear_project_file_download_cache",
]
