"""Render-artifact invalidation for preview, editor, image, and PDF workflows."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any


def clear_pdf_artifacts(state: MutableMapping[str, Any], status: str = "Not created") -> None:
    """Drop cached PDF bytes, signatures, and export-only transient caches."""

    from app_modules.pdf_artifact_state import clear_pdf_artifact_state

    clear_pdf_artifact_state(state, status=status)


def mark_pdf_dirty(state: MutableMapping[str, Any], status: str = "Needs refresh") -> None:
    """Invalidate PDF artifacts and the cloud-saved marker after content changes."""

    clear_pdf_artifacts(state, status=status)
    from app_modules.project_session_cleanup import clear_project_save_marker

    clear_project_save_marker(state)


__all__ = ["clear_pdf_artifacts", "mark_pdf_dirty"]
