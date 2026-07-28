"""Streamlit runtime adapter for the project-storage repository."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from app_modules.performance_telemetry import record_supabase_request, telemetry_is_active
from project_storage.config import supabase_config_from_mapping
from project_storage.http_client import SupabaseHttpClient
from project_storage.repository import ProjectStorageRepository

_REPOSITORY_STATE_KEY = "project_storage_repository"


def get_project_storage_repository() -> ProjectStorageRepository | None:
    """Return the session repository, or ``None`` when storage is unconfigured."""

    cached = st.session_state.get(_REPOSITORY_STATE_KEY)
    if isinstance(cached, ProjectStorageRepository):
        return cached
    config = supabase_config_from_mapping(_streamlit_secrets_mapping())
    if config is None:
        return None
    client = SupabaseHttpClient(config, observer=_observe_supabase_request)
    repository = ProjectStorageRepository(config, client=client)
    st.session_state[_REPOSITORY_STATE_KEY] = repository
    return repository


def project_storage_is_configured() -> bool:
    return get_project_storage_repository() is not None


def _streamlit_secrets_mapping() -> Mapping[str, Any]:
    try:
        return st.secrets
    except Exception:
        return {}


def _observe_supabase_request(event: Mapping[str, Any]) -> None:
    """Forward sanitized request metadata into the current Streamlit session."""

    if telemetry_is_active(st.session_state):
        record_supabase_request(st.session_state, event)
