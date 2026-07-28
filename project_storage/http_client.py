"""Minimal Supabase REST and Storage HTTP client."""

from __future__ import annotations

from collections.abc import Callable
import json
from time import perf_counter
from typing import Any, Mapping
from urllib import parse

from project_storage.http_transport import HttpTransport, PersistentHttpTransport

from project_storage.config import SupabaseStorageConfig


class SupabaseRequestError(RuntimeError):
    """Raised when Supabase returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        endpoint: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.endpoint = endpoint


RequestObserver = Callable[[Mapping[str, Any]], None]


class SupabaseHttpClient:
    """Small stdlib-only client for Supabase PostgREST and Storage APIs."""

    def __init__(
        self,
        config: SupabaseStorageConfig,
        *,
        timeout: float = 20.0,
        observer: RequestObserver | None = None,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._timeout = timeout
        self._observer = observer
        self._request_sequence = 0
        self._transport = transport or PersistentHttpTransport(config.url, timeout=timeout)

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
        request_headers = {
            "apikey": self._config.secret_key,
            "Authorization": f"Bearer {self._config.secret_key}",
            **(headers or {}),
        }
        self._request_sequence += 1
        request_id = f"supabase-{self._request_sequence}"
        started = perf_counter()
        try:
            response = self._transport.request(
                method,
                path,
                data=data,
                headers=request_headers,
            )
        except Exception as exc:
            self._notify_observer(
                method=method,
                path=path,
                request_id=request_id,
                seconds=perf_counter() - started,
                ok=False,
                status=None,
                request_bytes=len(data or b""),
                response_bytes=0,
                error_type=type(exc).__name__,
            )
            raise SupabaseRequestError(
                f"Supabase {method} {_safe_endpoint(path)} failed: {exc}",
                endpoint=_safe_endpoint(path),
            ) from exc

        body = response.body
        status = int(response.status)
        ok = 200 <= status < 300
        self._notify_observer(
            method=method,
            path=path,
            request_id=request_id,
            seconds=perf_counter() - started,
            ok=ok,
            status=status,
            request_bytes=len(data or b""),
            response_bytes=len(body),
            error_type="" if ok else "HTTPError",
        )
        if not ok:
            message = body.decode("utf-8", errors="replace")[:1000]
            raise SupabaseRequestError(
                f"Supabase {method} {_safe_endpoint(path)} failed: {status} {message}",
                status=status,
                endpoint=_safe_endpoint(path),
            )
        return body, _normalized_headers(response.headers)

    def close(self) -> None:
        """Release the pooled HTTP connection owned by this client."""

        self._transport.close()

    def _notify_observer(
        self,
        *,
        method: str,
        path: str,
        request_id: str,
        seconds: float,
        ok: bool,
        status: int | None,
        request_bytes: int,
        response_bytes: int,
        error_type: str = "",
    ) -> None:
        if self._observer is None:
            return
        event = {
            "method": str(method or "").upper(),
            "endpoint": _safe_endpoint(path),
            "request_id": request_id,
            "seconds": max(0.0, float(seconds or 0.0)),
            "ok": bool(ok),
            "status": status,
            "request_bytes": max(0, int(request_bytes or 0)),
            "response_bytes": max(0, int(response_bytes or 0)),
            "error_type": str(error_type or "")[:80],
        }
        try:
            self._observer(event)
        except Exception:
            return


def _safe_endpoint(path: str) -> str:
    clean_path = str(path or "").split("?", 1)[0].strip("/")
    parts = [part for part in clean_path.split("/") if part]
    if parts[:3] == ["rest", "v1", "rpc"]:
        return f"rpc:{parts[3] if len(parts) > 3 else 'unknown'}"
    if parts[:2] == ["rest", "v1"]:
        return f"rest:{parts[2] if len(parts) > 2 else 'unknown'}"
    if parts[:3] == ["storage", "v1", "object"]:
        return "storage:object"
    return ":".join(parts[:3]) or "unknown"


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
