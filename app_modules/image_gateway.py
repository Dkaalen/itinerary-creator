"""Image-bank gateway rules for the Add Pictures workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImageBankGatewayResult:
    """Decision returned before the app enters picture review."""

    ready: bool
    status: dict[str, Any]
    attempted_connection: bool = False
    setup_status: dict[str, Any] | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": dict(self.status or {}),
            "attempted_connection": self.attempted_connection,
            "setup_status": dict(self.setup_status or {}),
            "message": self.message,
        }


def image_bank_is_ready_for_client_pictures(status: Mapping[str, Any] | None) -> bool:
    """Return True only when a real destination image bank is available."""

    status = status or {}
    if "required_destinations_ready" in status:
        return bool(status.get("required_destinations_ready"))
    return bool(status.get("full_bank_found") and not status.get("missing_full_bank"))


def _blocking_message(status: Mapping[str, Any] | None, setup_status: Mapping[str, Any] | None = None) -> str:
    status = status or {}
    setup_status = setup_status or {}
    return str(
        status.get("blocking_message")
        or setup_status.get("message")
        or "Full destination image bank is missing. Connect the separate itinerary-image-bank repository before picture review."
    )


def build_image_bank_gateway_result(
    status: Mapping[str, Any] | None,
    *,
    attempted_connection: bool = False,
    setup_status: Mapping[str, Any] | None = None,
) -> ImageBankGatewayResult:
    """Build a normalized gateway decision from image-bank diagnostics."""

    status_dict = dict(status or {})
    setup_dict = dict(setup_status or status_dict.get("setup_status") or {})
    ready = image_bank_is_ready_for_client_pictures(status_dict)
    return ImageBankGatewayResult(
        ready=ready,
        status=status_dict,
        attempted_connection=bool(attempted_connection),
        setup_status=setup_dict,
        message="" if ready else _blocking_message(status_dict, setup_dict),
    )


def connect_image_bank_for_picture_stage(
    status_func: Callable[[], Mapping[str, Any]],
    connect_func: Callable[[], Mapping[str, Any]],
) -> ImageBankGatewayResult:
    """Try to connect the full image bank before entering picture review.

    The normal Add Pictures workflow must never silently proceed with only the
    bundled Default bank.  This helper keeps that rule outside the Streamlit
    view, which makes it easy to test and harder to bypass accidentally.
    """

    current_status = dict(status_func() or {})
    if image_bank_is_ready_for_client_pictures(current_status):
        return build_image_bank_gateway_result(current_status)

    connected_status = dict(connect_func() or {})
    return build_image_bank_gateway_result(
        connected_status,
        attempted_connection=True,
        setup_status=connected_status.get("setup_status") if isinstance(connected_status.get("setup_status"), Mapping) else None,
    )
