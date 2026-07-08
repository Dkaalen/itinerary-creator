"""Derived test group catalog metadata."""

from __future__ import annotations

from .core import (
    ACTIVITY_TESTS,
    ARCHITECTURE_TESTS,
    CRITICAL_TESTS,
    FAST_TESTS,
    PARSER_TESTS,
)
from .quality import PDF_TESTS, QUALITY_TESTS, SLOW_TESTS
from .ui_workflow import (
    CALCULATOR_TESTS,
    DAY_BRAIN_TESTS,
    EDITOR_TESTS,
    IMAGE_TESTS,
    STORAGE_TESTS,
    UI_TESTS,
    WORKFLOW_TESTS,
)

GROUPS = {
    "critical": CRITICAL_TESTS,
    "fast": FAST_TESTS,
    "parser": PARSER_TESTS,
    "activity": ACTIVITY_TESTS,
    "architecture": ARCHITECTURE_TESTS,
    "calculator": CALCULATOR_TESTS,
    "editor": EDITOR_TESTS,
    "images": IMAGE_TESTS,
    "storage": STORAGE_TESTS,
    "ui": UI_TESTS,
    "workflow": WORKFLOW_TESTS,
    "quality": QUALITY_TESTS,
    "pdf": PDF_TESTS,
    "slow": SLOW_TESTS,
}

GROUP_ORDER = tuple(GROUPS)

HEALTH_CHECK_GROUPS = ("critical",)

RELEASE_CANDIDATE_GROUPS = (
    "critical",
    "fast",
    "calculator",
    "storage",
    "workflow",
    "parser",
    "activity",
    "architecture",
    "editor",
    "images",
    "ui",
    "quality",
    "pdf",
)

CI_MATRIX_GROUPS = (
    "critical",
    "fast",
    "calculator",
    "storage",
    "workflow",
    "architecture",
    "parser",
    "activity",
    "editor",
    "images",
    "ui",
)

GROUP_DESCRIPTIONS = {
    "critical": "instant smoke/contracts for critical app surfaces and known failure classes",
    "fast": "small everyday safety gate with PDF/slow/large quality checks excluded",
    "parser": "text cleanup, date/time, extractor, and normalizer regressions",
    "activity": "activity product rules, catalogue matching, source fidelity, and QA warnings",
    "architecture": "structured model boundaries, render ownership, and test-runner infrastructure",
    "calculator": "calculator state, grid payloads, local library, and workbook export",
    "editor": "typed draft ownership, autosave, visual editor, and editor/PDF state safety",
    "images": "image-bank paths, matching, auditing, destination pictures, and image QA",
    "storage": "project identity, Supabase repository, file save/load, and cloud browser behavior",
    "ui": "Streamlit workflow shell, export readiness, image gateway, and UI boundary tests",
    "workflow": "hosted app flow, stage transitions, editor/export state, and runtime guardrails",
    "quality": "medium itinerary quality and content/rendering regressions",
    "pdf": "PDF export and preview/PDF parity checks",
    "slow": "isolated large-fixture and PDF-heavy stability checks",
    "health": "instant local health check: compile/import plus the critical smoke lane",
    "release": "strong timeout-safe release candidate check without the isolated slow harness",
}
