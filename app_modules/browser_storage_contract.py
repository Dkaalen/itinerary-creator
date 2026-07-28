"""Authoritative browser-recovery storage contract shared by all frontends."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_DAY_MS = 24 * 60 * 60 * 1000

_BROWSER_STORAGE_CONTRACT: dict[str, Any] = {
    "schema_version": 1,
    "indexed_db": {
        "name": "itineraryCreatorRecovery",
        "version": 1,
        "store": "drafts",
    },
    "cleanup_session_key": "itineraryCreatorRecoveryCleanup.v1",
    "owners": {
        "calculator": {
            "current_prefix": "itineraryCalculatorBrowserDraft.v3.",
            "legacy_prefixes": [
                "itineraryCalculatorBrowserDraft.v1.",
                "itineraryCalculatorBrowserDraft.v2.",
                "itineraryCalculatorDraft.",
                "calculatorDraft.",
            ],
            "recovery_suffix": ".versions",
            "max_age_ms": 7 * _DAY_MS,
            "max_namespaces": 3,
            "max_total_bytes": 1536 * 1024,
            "max_namespace_bytes": 1250 * 1024,
            "max_draft_bytes": 900 * 1024,
            "max_snapshots": 5,
            "recovery_schema_version": 4,
        },
        "visual_editor": {
            "current_prefix": "itinerary-visual-editor-draft:",
            "legacy_prefixes": ["itineraryVisualEditorDraft."],
            "max_age_ms": 7 * _DAY_MS,
            "max_namespaces": 3,
            "max_total_bytes": 1024 * 1024,
            "max_draft_bytes": 700 * 1024,
        },
    },
}


def browser_storage_contract() -> dict[str, Any]:
    """Return an isolated copy safe to place in component payloads."""

    return deepcopy(_BROWSER_STORAGE_CONTRACT)


__all__ = ["browser_storage_contract"]
