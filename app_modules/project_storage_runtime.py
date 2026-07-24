"""Streamlit runtime adapter for the project-storage repository."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from project_storage.config import supabase_config_from_mapping
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
    repository = ProjectStorageRepository(config)
    st.session_state[_REPOSITORY_STATE_KEY] = repository
    return repository


def project_storage_is_configured() -> bool:
    return get_project_storage_repository() is not None


def _streamlit_secrets_mapping() -> Mapping[str, Any]:
    try:
        return st.secrets
    except Exception:
        return {}
