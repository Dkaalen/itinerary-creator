"""Minimal Supabase REST and Storage HTTP client."""

from __future__ import annotations

import json
from typing import Any, Mapping
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

    def rest_get_with_count(
        self,
        table: str,
        params: dict[str, str],
    ) -> tuple[list[dict[str, Any]], int]:
        """Return rows plus PostgREST's exact total for the filtered query."""

        query = parse.urlencode(params)
        body, headers = self._request_with_headers(
            "GET",
            f"/rest/v1/{table}?{query}",
            headers={"Prefer": "count=exact"},
        )
        rows = _decode_rows(body)
        return rows, _content_range_total(headers.get("content-range"), fallback=len(rows))

    def rest_insert(self, table: str, payload: dict[str, Any], *, upsert: bool = False) -> list[dict[str, Any]]:
        prefer = "return=representation"
        if upsert:
            prefer = "resolution=merge-duplicates,return=representation"
        return self._json_request("POST", f"/rest/v1/{table}", payload=payload, prefer=prefer)

    def rest_rpc(self, function_name: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Call one explicit PostgREST RPC function and return object rows."""

        encoded_name = parse.quote(str(function_name or "").strip(), safe="")
        if not encoded_name:
            raise ValueError("Supabase RPC function name is required.")
        return self._json_request(
            "POST",
            f"/rest/v1/rpc/{encoded_name}",
            payload=dict(payload or {}),
            prefer="return=representation",
        )

    def rest_update(
        self,
        table: str,
        params: dict[str, str],
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Patch all rows matching the explicit PostgREST filters."""

        query = parse.urlencode(params)
        return self._json_request(
            "PATCH",
            f"/rest/v1/{table}?{query}",
            payload=payload,
            prefer="return=representation",
        )

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
        return _decode_rows(body)

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        body, _response_headers = self._request_with_headers(method, path, data=data, headers=headers)
        return body

    def _request_with_headers(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[bytes, dict[str, str]]:
        url = f"{self._config.url}{path}"
        request_headers = {
            "apikey": self._config.secret_key,
            "Authorization": f"Bearer {self._config.secret_key}",
            **(headers or {}),
        }
        req = request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                return response.read(), _normalized_headers(response.headers)
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise SupabaseRequestError(f"Supabase {method} {path} failed: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise SupabaseRequestError(f"Supabase {method} {path} failed: {exc.reason}") from exc


def _decode_rows(body: bytes) -> list[dict[str, Any]]:
    if not body:
        return []
    parsed = json.loads(body.decode("utf-8"))
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).casefold(): str(value) for key, value in headers.items()}


def _content_range_total(value: object, *, fallback: int) -> int:
    text = str(value or "").strip()
    if "/" not in text:
        return max(0, int(fallback))
    total = text.rsplit("/", 1)[-1].strip()
    if not total or total == "*":
        return max(0, int(fallback))
    try:
        return max(0, int(total))
    except ValueError:
        return max(0, int(fallback))
