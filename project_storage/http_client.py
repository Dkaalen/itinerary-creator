"""Minimal Supabase REST and Storage HTTP client."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from project_storage.config import SupabaseStorageConfig


class SupabaseRequestError(RuntimeError):
    """Raised when Supabase returns an error response."""


class SupabaseHttpClient:
    """Small stdlib-only client for Supabase PostgREST and Storage APIs."""

    def __init__(self, config: SupabaseStorageConfig, *, timeout: float = 20.0) -> None:
        self._config = config
        self._timeout = timeout

    def rest_get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        query = parse.urlencode(params)
        return self._json_request("GET", f"/rest/v1/{table}?{query}")

    def rest_insert(self, table: str, payload: dict[str, Any], *, upsert: bool = False) -> list[dict[str, Any]]:
        prefer = "return=representation"
        if upsert:
            prefer = "resolution=merge-duplicates,return=representation"
        return self._json_request("POST", f"/rest/v1/{table}", payload=payload, prefer=prefer)

    def rest_delete(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        query = parse.urlencode(params)
        return self._json_request("DELETE", f"/rest/v1/{table}?{query}", prefer="return=representation")

    def storage_upload(self, bucket: str, storage_path: str, content: bytes, *, content_type: str) -> None:
        encoded_path = parse.quote(storage_path.strip("/"), safe="/")
        headers = {"Content-Type": content_type, "x-upsert": "true"}
        self._request("POST", f"/storage/v1/object/{bucket}/{encoded_path}", data=content, headers=headers)

    def storage_download(self, bucket: str, storage_path: str) -> bytes:
        encoded_path = parse.quote(storage_path.strip("/"), safe="/")
        return self._request("GET", f"/storage/v1/object/{bucket}/{encoded_path}")

    def storage_delete(self, bucket: str, storage_paths: list[str]) -> None:
        cleaned_paths = [path.strip("/") for path in storage_paths if str(path or "").strip("/")]
        if not cleaned_paths:
            return
        payload = {"prefixes": cleaned_paths}
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        self._request("DELETE", f"/storage/v1/object/{bucket}", data=data, headers=headers)

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> list[dict[str, Any]]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        body = self._request(method, path, data=data, headers=headers)
        if not body:
            return []
        parsed = json.loads(body.decode("utf-8"))
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []

    def _request(self, method: str, path: str, *, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
        url = f"{self._config.url}{path}"
        request_headers = {
            "apikey": self._config.secret_key,
            "Authorization": f"Bearer {self._config.secret_key}",
            **(headers or {}),
        }
        req = request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                return response.read()
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise SupabaseRequestError(f"Supabase {method} {path} failed: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise SupabaseRequestError(f"Supabase {method} {path} failed: {exc.reason}") from exc
