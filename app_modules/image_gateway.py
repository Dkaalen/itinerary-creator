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


def _int_status_value(status: Mapping[str, Any], key: str) -> int:
    try:
        return int(status.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def destination_image_bank_is_ready_for_client_pictures(status: Mapping[str, Any] | None) -> bool:
    """Return True when the real destination image bank covers the itinerary.

    The picture workflow may fall back to bundled default images, but fallback
    must not be treated as a reason to skip the real destination-bank connection
    attempt.  When the itinerary has explicit destination requests, those packs
    are the readiness contract.  Without explicit requests, any visible full
    destination bank is enough.
    """

    status = status or {}
    required_destinations = status.get("required_destinations") or ()
    if required_destinations:
        return bool(status.get("required_destinations_ready"))
    if status.get("required_destinations_ready"):
        return True
    if status.get("full_bank_found") or status.get("using_full_destination_bank"):
        return True
    return _int_status_value(status, "destination_image_count") > 0


def fallback_image_source_is_available(status: Mapping[str, Any] | None) -> bool:
    """Return True when bundled/non-destination images can keep review usable."""

    status = status or {}
    if status.get("default_only") or status.get("is_default_only"):
        return True
    if _int_status_value(status, "default_image_count") > 0:
        return True
    # Last-resort compatibility for legacy diagnostics that only exposed a
    # total count.  The destination-ready helper above owns the real-bank case.
    return _int_status_value(status, "total_image_count") > 0


def image_bank_is_ready_for_client_pictures(status: Mapping[str, Any] | None) -> bool:
    """Return True when the picture workflow has any usable image source.

    A connected destination bank is preferred, but the workflow may still
    proceed with bundled fallbacks after the app has tried to connect the real
    destination packs.
    """

    return destination_image_bank_is_ready_for_client_pictures(status) or fallback_image_source_is_available(status)


def image_bank_should_attempt_destination_connection(status: Mapping[str, Any] | None) -> bool:
    """Return True when the app should try to repair/fetch destination packs."""

    return not destination_image_bank_is_ready_for_client_pictures(status)


def _blocking_message(status: Mapping[str, Any] | None, setup_status: Mapping[str, Any] | None = None) -> str:
    status = status or {}
    setup_status = setup_status or {}
    return str(
        status.get("blocking_message")
        or setup_status.get("message")
        or "No usable itinerary images are available. Add pictures after connecting an image bank or bundled fallback images."
    )


def _setup_status_from(status: Mapping[str, Any] | None) -> dict[str, Any]:
    status = status or {}
    setup_status = status.get("setup_status")
    if isinstance(setup_status, Mapping):
        return dict(setup_status)
    if any(key in status for key in ("ok", "code", "message", "error", "method", "git_error")):
        return dict(status)
    return {}


def _status_with_setup(status: Mapping[str, Any] | None, setup_status: Mapping[str, Any] | None) -> dict[str, Any]:
    value = dict(status or {})
    setup_dict = dict(setup_status or {})
    if setup_dict:
        value["setup_status"] = setup_dict
    return value


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
    """Prefer the real destination bank before entering picture review.

    Bundled fallback pictures are allowed only as a graceful fallback after the
    destination-bank repair/fetch path has been attempted for the current
    itinerary.  This prevents the tiny bundled Default bank from short-circuiting
    the real image-bank connection.
    """

    current_status = dict(status_func() or {})
    if not image_bank_should_attempt_destination_connection(current_status):
        return build_image_bank_gateway_result(current_status)

    connected_status = dict(connect_func() or {})
    setup_status = _setup_status_from(connected_status)

    if image_bank_is_ready_for_client_pictures(connected_status):
        return build_image_bank_gateway_result(
            connected_status,
            attempted_connection=True,
            setup_status=setup_status,
        )

    if image_bank_is_ready_for_client_pictures(current_status):
        return build_image_bank_gateway_result(
            _status_with_setup(current_status, setup_status),
            attempted_connection=True,
            setup_status=setup_status,
        )

    return build_image_bank_gateway_result(
        _status_with_setup(connected_status or current_status, setup_status),
        attempted_connection=True,
        setup_status=setup_status,
    )
