"""Small persistent HTTP transport for Supabase REST and Storage requests."""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import ssl
from threading import Lock
from typing import Mapping, Protocol
from urllib import parse


@dataclass(frozen=True)
class HttpTransportResponse:
    """Fully-read response returned by a transport implementation."""

    status: int
    headers: dict[str, str]
    body: bytes


class HttpTransport(Protocol):
    """Minimal request transport used by :class:`SupabaseHttpClient`."""

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None,
        headers: Mapping[str, str],
    ) -> HttpTransportResponse: ...

    def close(self) -> None: ...


class PersistentHttpTransport:
    """Reuse one verified HTTP(S) connection and reconnect once when stale."""

    def __init__(self, base_url: str, *, timeout: float = 20.0) -> None:
        parsed = parse.urlsplit(str(base_url or "").rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Supabase URL must be an absolute HTTP or HTTPS URL.")
        self._scheme = parsed.scheme
        self._host = parsed.hostname
        self._port = parsed.port
        self._base_path = parsed.path.rstrip("/")
        self._timeout = max(1.0, float(timeout))
        self._connection: http.client.HTTPConnection | None = None
        self._lock = Lock()

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None,
        headers: Mapping[str, str],
    ) -> HttpTransportResponse:
        request_path = f"{self._base_path}/{str(path or '').lstrip('/')}"
        if not request_path.startswith("/"):
            request_path = f"/{request_path}"
        with self._lock:
            for attempt in range(2):
                connection = self._connection_or_create()
                try:
                    connection.request(
                        str(method or "GET").upper(),
                        request_path,
                        body=data,
                        headers=dict(headers),
                    )
                    response = connection.getresponse()
                    body = response.read()
                    result = HttpTransportResponse(
                        status=int(response.status),
                        headers={str(key).casefold(): str(value) for key, value in response.getheaders()},
                        body=body,
                    )
                    if response.will_close:
                        self._close_unlocked()
                    return result
                except (
                    BrokenPipeError,
                    ConnectionResetError,
                    http.client.CannotSendRequest,
                    http.client.RemoteDisconnected,
                    http.client.ResponseNotReady,
                    OSError,
                ):
                    self._close_unlocked()
                    if attempt:
                        raise
        raise RuntimeError("HTTP request could not be completed.")

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _connection_or_create(self) -> http.client.HTTPConnection:
        if self._connection is None:
            if self._scheme == "https":
                self._connection = http.client.HTTPSConnection(
                    self._host,
                    self._port,
                    timeout=self._timeout,
                    context=ssl.create_default_context(),
                )
            else:
                self._connection = http.client.HTTPConnection(
                    self._host,
                    self._port,
                    timeout=self._timeout,
                )
        return self._connection

    def _close_unlocked(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass


__all__ = ["HttpTransport", "HttpTransportResponse", "PersistentHttpTransport"]
