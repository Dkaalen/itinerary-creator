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

from .domains import EXPORT_TESTS, FAILURE_MODE_TESTS, GENERATOR_TESTS, INCLUSION_TESTS, ROUTE_TESTS

from .focused_workflows import (
    CALCULATOR_BROWSER_WORKFLOW_TESTS, FORMULA_WORKFLOW_TESTS, VALIDATION_WORKFLOW_TESTS,
    WORKBOOK_WORKFLOW_TESTS, REALISTIC_CALCULATOR_WORKFLOW_TESTS,
    PROJECT_MANAGEMENT_WORKFLOW_TESTS, ROLLBACK_WORKFLOW_TESTS,
    CLOUD_LIFECYCLE_WORKFLOW_TESTS, RECONSTRUCTION_WORKFLOW_TESTS,
    GENERATION_WORKFLOW_TESTS, EDITOR_PICTURES_WORKFLOW_TESTS,
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
    "calculator-browser": CALCULATOR_BROWSER_WORKFLOW_TESTS,
    "formulas": FORMULA_WORKFLOW_TESTS,
    "validation": VALIDATION_WORKFLOW_TESTS,
    "workbook": WORKBOOK_WORKFLOW_TESTS,
    "calculator-realistic": REALISTIC_CALCULATOR_WORKFLOW_TESTS,
    "project-management": PROJECT_MANAGEMENT_WORKFLOW_TESTS,
    "rollback": ROLLBACK_WORKFLOW_TESTS,
    "cloud-lifecycle": CLOUD_LIFECYCLE_WORKFLOW_TESTS,
    "reconstruction": RECONSTRUCTION_WORKFLOW_TESTS,
    "generation": GENERATION_WORKFLOW_TESTS,
    "editor-pictures": EDITOR_PICTURES_WORKFLOW_TESTS,
    "generator": GENERATOR_TESTS,
    "routes": ROUTE_TESTS,
    "inclusions": INCLUSION_TESTS,
    "export": EXPORT_TESTS,
    "failure-modes": FAILURE_MODE_TESTS,
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
    "calculator-browser": "one explicit stage per Calculator Chromium workflow and protocol contract",
    "formulas": "formula evaluation, financial parity, dependency chains, and currency behavior",
    "validation": "action-scoped validation and Local Library workbook diagnostics",
    "workbook": "Calculator Excel import, export, template, and package preservation",
    "calculator-realistic": "realistic Calculator use and workflow invariants",
    "project-management": "project identity, switching, duplication, rename, and current-version saves",
    "rollback": "transactional project save and reconstruction rollback",
    "cloud-lifecycle": "cloud open, save, download, delete, and browser lifecycle",
    "reconstruction": "saved-project reconstruction authority and supported rebuild paths",
    "generation": "Calculator handoff and hosted itinerary generation transitions",
    "editor-pictures": "editor draft, picture selection, image safety, and autosave integration",
    "generator": "generator, render-artifact, and prepared-document ownership",
    "routes": "Streamlit routes, transport facts, destination routes, and continuity",
    "inclusions": "structured inclusions, exclusions, source identity, and PDF projection",
    "export": "PDF, Excel, readiness, artifact, and export-state contracts",
    "failure-modes": "timeouts, recovery, rollback, diagnostics, and resilient state transitions",
    "health": "instant local health check: compile/import plus the critical smoke lane",
    "release": "strong timeout-safe release candidate check without the isolated slow harness",
}
