"""Supabase project-storage configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SupabaseStorageConfig:
    """Connection values needed for server-side Supabase storage."""

    url: str
    secret_key: str
    bucket: str

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.secret_key and self.bucket)


def supabase_config_from_mapping(values: Mapping[str, Any] | None) -> SupabaseStorageConfig | None:
    """Build config from Streamlit secrets or another mapping."""

    if not values:
        return None
    url = _clean(values.get("SUPABASE_URL"))
    secret_key = _clean(values.get("SUPABASE_SECRET_KEY"))
    bucket = _clean(values.get("SUPABASE_BUCKET")) or "itinerary-files"
    config = SupabaseStorageConfig(url=_strip_rest_suffix(url), secret_key=secret_key, bucket=bucket)
    return config if config.is_configured else None


def _clean(value: Any) -> str:
    return str(value or "").strip().strip('"').strip("'")


def _strip_rest_suffix(url: str) -> str:
    return url.removesuffix("/rest/v1/").removesuffix("/rest/v1").rstrip("/")
