"""Shared image-bank readiness gate for picture/export stages."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.image_gateway_ui import (
    _current_image_bank_status,
    _image_status_notice,
    _render_image_bank_gateway_repair,
)


def render_image_bank_gate(state: MutableMapping[str, Any]) -> bool:
    """Render the shared image-bank gate and return whether the stage can continue."""

    status = _current_image_bank_status()
    if not image_bank_is_ready_for_client_pictures(status):
        state["image_bank_gateway"] = {
            "ready": False,
            "status": status,
            "message": status.get("blocking_message", ""),
        }
        _render_image_bank_gateway_repair(state.get("image_bank_gateway"))
        return False
    _image_status_notice()
    return True
