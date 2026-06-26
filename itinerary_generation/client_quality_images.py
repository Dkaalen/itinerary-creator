"""Image payload and image-bank checks for client output."""

from typing import Any, Mapping
from itinerary_generation.generation_quality_gate import WARNING, ItineraryValidationIssue


def image_payload_is_default(match: Mapping[str, Any]) -> bool:
    if bool(match.get("is_default") or match.get("is_generic")): return True
    city, filename, path = str(match.get("city", "") or "").strip().lower(), str(match.get("filename", "") or "").strip().lower(), str(match.get("path", "") or "").replace("\\", "/").lower()
    return city in {"default", "defoult"} or "/default/" in path or filename.startswith("default_")


def image_match_issues(day_images):
    return []


def image_bank_status_issues(status: Mapping[str, Any] | None) -> list[ItineraryValidationIssue]:
    if not isinstance(status, Mapping): return []
    missing = bool(status.get("missing_full_bank") or status.get("default_only") or status.get("is_default_only") or not status.get("full_bank_found", status.get("using_full_destination_bank", False)))
    if not missing: return []
    return [ItineraryValidationIssue(WARNING, "image_bank_full_missing", str(status.get("blocking_message") or "Full destination image bank is missing; bundled fallback pictures may be used until the destination image bank is connected."), context=str(status.get("source_path") or status.get("paths") or ""))]
