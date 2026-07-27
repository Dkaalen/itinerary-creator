"""Lazy image API for the itinerary app.

The package exposes the established image-matching and image-bank compatibility
surface without importing every image implementation module at package import.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = (
    "CITY_ALIASES",
    "IMAGE_EXTENSIONS",
    "SEASON_ALIASES",
    "SUMMER_MONTHS",
    "THEME_ALIASES",
    "WINTER_MONTHS",
    "ImageAuditWarning",
    "ImageCandidate",
    "ImageBankIndex",
    "DestinationRequest",
    "_candidate_destination_matches",
    "_candidate_to_payload",
    "_coerce_image_bank_paths",
    "_is_global_default_candidate",
    "_score_default_candidate",
    "_season_available_for_context",
    "_select_best_candidate_for_context",
    "audit_day_image_match",
    "audit_day_image_matches",
    "build_day_context",
    "candidate_destination_matches",
    "candidate_to_payload",
    "city_variants",
    "connect_remote_image_bank_if_missing",
    "destination_requests_from_rows",
    "coerce_image_bank_paths",
    "extract_image_metadata",
    "ensure_runtime_image_bank",
    "ensure_runtime_image_bank_status",
    "ensure_destination_packs",
    "format_match_for_debug",
    "get_image_bank_diagnostics",
    "image_bank_debug_payload",
    "image_bank_status",
    "image_bank_status_for_paths",
    "image_bank_status_summary",
    "image_bank_manifest_url",
    "get_image_bank_index",
    "invalidate_image_bank_cache",
    "day_image_matches_from_preview_html",
    "merge_preview_image_contract",
    "commit_selection_payload",
    "read_selection_commit",
    "selection_input_signature",
    "store_selection_commit",
    "prefetch_image_bank_for_rows",
    "infer_primary_month_from_rows",
    "infer_season_from_rows",
    "infer_seasons",
    "infer_themes",
    "is_global_default_candidate",
    "normalize_keyword",
    "scan_image_bank",
    "score_default_candidate",
    "score_image_for_day",
    "season_available_for_context",
    "select_best_candidate_for_context",
    "select_day_image",
    "select_day_images",
    "tokenize",
)

_MODULE_EXPORTS = frozenset(
    {
        "app_image_bank",
        "app_image_selection",
        "day_image_selection",
        "day_image_ui",
        "destination_image_library",
        "diagnostics",
        "fallback",
        "image_bank",
        "image_bank_bootstrap",
        "image_bank_bootstrap_status",
        "image_bank_discovery",
        "image_bank_fetch",
        "image_bank_index",
        "image_bank_paths",
        "image_bank_scan",
        "image_bank_settings",
        "image_bank_status",
        "image_match_audit",
        "image_overrides",
        "image_preview",
        "image_uploads",
        "image_workflow_review",
        "matcher",
        "matcher_context",
        "matcher_destination_context",
        "matcher_scoring",
        "matcher_selection",
        "matcher_service_context",
        "metadata",
        "preview_image_contract",
        "remote_archive_install",
        "remote_distribution",
        "remote_distribution_config",
        "remote_distribution_locking",
        "remote_distribution_models",
        "remote_distribution_prefetch",
        "remote_distribution_requests",
        "remote_manifest",
        "remote_pack_resolver",
        "replacement_options",
        "scanner",
        "seasonal_policy",
        "selection_commit",
        "selection_contract",
    }
)

_SYMBOL_EXPORTS: dict[str, tuple[str, str]] = {
    "format_match_for_debug": ("diagnostics", "format_match_for_debug"),
    "get_image_bank_diagnostics": ("diagnostics", "get_image_bank_diagnostics"),
    "image_bank_debug_payload": ("diagnostics", "image_bank_debug_payload"),
    "image_bank_status_summary": ("diagnostics", "image_bank_status_summary"),
    "connect_remote_image_bank_if_missing": ("image_bank", "connect_remote_image_bank_if_missing"),
    "destination_requests_from_rows": ("image_bank", "destination_requests_from_rows"),
    "ensure_runtime_image_bank": ("image_bank", "ensure_runtime_image_bank"),
    "ensure_runtime_image_bank_status": ("image_bank", "ensure_runtime_image_bank_status"),
    "image_bank_status": ("image_bank", "image_bank_status"),
    "image_bank_status_for_paths": ("image_bank", "image_bank_status_for_paths"),
    "prefetch_image_bank_for_rows": ("image_bank", "prefetch_image_bank_for_rows"),
    "DestinationRequest": ("remote_distribution", "DestinationRequest"),
    "ensure_destination_packs": ("remote_distribution", "ensure_destination_packs"),
    "image_bank_manifest_url": ("remote_distribution", "image_bank_manifest_url"),
    "_is_global_default_candidate": ("fallback", "_is_global_default_candidate"),
    "_score_default_candidate": ("fallback", "_score_default_candidate"),
    "is_global_default_candidate": ("fallback", "is_global_default_candidate"),
    "score_default_candidate": ("fallback", "score_default_candidate"),
    "_candidate_destination_matches": ("matcher", "_candidate_destination_matches"),
    "_candidate_to_payload": ("matcher", "_candidate_to_payload"),
    "_season_available_for_context": ("matcher", "_season_available_for_context"),
    "_select_best_candidate_for_context": ("matcher", "_select_best_candidate_for_context"),
    "build_day_context": ("matcher", "build_day_context"),
    "candidate_destination_matches": ("matcher", "candidate_destination_matches"),
    "candidate_to_payload": ("matcher", "candidate_to_payload"),
    "score_image_for_day": ("matcher", "score_image_for_day"),
    "season_available_for_context": ("matcher", "season_available_for_context"),
    "select_best_candidate_for_context": ("matcher", "select_best_candidate_for_context"),
    "select_day_image": ("matcher", "select_day_image"),
    "select_day_images": ("matcher", "select_day_images"),
    "ImageAuditWarning": ("image_match_audit", "ImageAuditWarning"),
    "audit_day_image_match": ("image_match_audit", "audit_day_image_match"),
    "audit_day_image_matches": ("image_match_audit", "audit_day_image_matches"),
    "CITY_ALIASES": ("metadata", "CITY_ALIASES"),
    "IMAGE_EXTENSIONS": ("metadata", "IMAGE_EXTENSIONS"),
    "SEASON_ALIASES": ("metadata", "SEASON_ALIASES"),
    "SUMMER_MONTHS": ("metadata", "SUMMER_MONTHS"),
    "THEME_ALIASES": ("metadata", "THEME_ALIASES"),
    "WINTER_MONTHS": ("metadata", "WINTER_MONTHS"),
    "ImageCandidate": ("metadata", "ImageCandidate"),
    "city_variants": ("metadata", "city_variants"),
    "extract_image_metadata": ("metadata", "extract_image_metadata"),
    "infer_primary_month_from_rows": ("metadata", "infer_primary_month_from_rows"),
    "infer_season_from_rows": ("metadata", "infer_season_from_rows"),
    "infer_seasons": ("metadata", "infer_seasons"),
    "infer_themes": ("metadata", "infer_themes"),
    "normalize_keyword": ("metadata", "normalize_keyword"),
    "tokenize": ("metadata", "tokenize"),
    "ImageBankIndex": ("scanner", "ImageBankIndex"),
    "_coerce_image_bank_paths": ("scanner", "_coerce_image_bank_paths"),
    "coerce_image_bank_paths": ("scanner", "coerce_image_bank_paths"),
    "get_image_bank_index": ("scanner", "get_image_bank_index"),
    "invalidate_image_bank_cache": ("scanner", "invalidate_image_bank_cache"),
    "scan_image_bank": ("scanner", "scan_image_bank"),
    "day_image_matches_from_preview_html": ("preview_image_contract", "day_image_matches_from_preview_html"),
    "merge_preview_image_contract": ("preview_image_contract", "merge_preview_image_contract"),
    "commit_selection_payload": ("selection_contract", "commit_selection_payload"),
    "read_selection_commit": ("selection_commit", "read_selection_commit"),
    "selection_input_signature": ("selection_commit", "selection_input_signature"),
    "store_selection_commit": ("selection_commit", "store_selection_commit"),
}


def __getattr__(name: str) -> Any:
    if name in _MODULE_EXPORTS:
        value = import_module(f".{name}", __name__)
    else:
        target = _SYMBOL_EXPORTS.get(name)
        if target is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        module_name, attribute_name = target
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, attribute_name)

    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_MODULE_EXPORTS))
