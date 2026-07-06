"""Human image-bank readiness messages for normal workflow UI."""

from __future__ import annotations

from collections.abc import Mapping

from app_modules.image_gateway import destination_image_bank_is_ready_for_client_pictures, fallback_image_source_is_available


def image_bank_readiness_label(status: Mapping[str, object] | None) -> str:
    """Return a compact status label for the currently available image source."""

    status = status or {}
    if destination_image_bank_is_ready_for_client_pictures(status):
        return "Destination images ready"
    if fallback_image_source_is_available(status):
        return "Fallback images available"
    return "Images not ready"


def image_bank_readiness_message(status: Mapping[str, object] | None) -> str:
    """Return calm user-facing image-bank copy without exposing connector internals."""

    status = status or {}
    destination_count = _int_value(status, "destination_image_count")
    default_count = _int_value(status, "default_image_count")
    required = len(status.get("required_destinations") or ())
    covered = len(status.get("covered_destinations") or ())

    if destination_image_bank_is_ready_for_client_pictures(status):
        suffix = f" for {covered}/{required} itinerary destinations" if required else ""
        return f"Destination images are ready{suffix}. {destination_count} pictures are available."
    if fallback_image_source_is_available(status):
        count_text = f" {default_count} fallback pictures are available." if default_count else ""
        return f"Destination images are unavailable, so the app will use fallback images for review.{count_text}"
    return str(status.get("blocking_message") or "No usable itinerary images are available yet.")


def image_bank_repair_message(status: Mapping[str, object] | None) -> str:
    """Return a concise blocker message for image-bank repair panels."""

    status = status or {}
    if fallback_image_source_is_available(status):
        return "Destination images could not be prepared. Fallback images are available for review."
    return str(status.get("blocking_message") or "Connect destination or fallback images before picture review.")


def _int_value(status: Mapping[str, object], key: str) -> int:
    try:
        return int(status.get(key) or 0)
    except (TypeError, ValueError):
        return 0
