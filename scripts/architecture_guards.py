"""Source-level architecture guard helpers for the Itinerary App.

The tests use this module to keep the normal PDF-producing workflow clean while
allowing debug/review code to remain in explicit debug modules.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SourceHit:
    path: str
    marker: str


@dataclass(frozen=True)
class SizeHit:
    path: str
    lines: int
    limit: int


@dataclass(frozen=True)
class FunctionHit:
    path: str
    name: str
    lines: int
    limit: int


NORMAL_WORKFLOW_SOURCES = (
    "app_modules/main_view.py",
    "app_modules/input_step.py",
    "app_modules/preview_step.py",
    "app_modules/picture_step.py",
    "app_modules/export_page.py",
    "app_modules/workflow_shell.py",
    "app_modules/workflow_actions.py",
    "app_modules/generation_action.py",
    "app_modules/project_load_action.py",
    "app_modules/image_stage_action.py",
    "app_modules/export_stage_action.py",
    "visual_editor_component/frontend/js/render.js",
    "visual_editor_component/frontend/js/editor_shell.js",
    "visual_editor_component/frontend/js/editor_dirty_state.js",
    "visual_editor_component/frontend/js/state.js",
)

NORMAL_WORKFLOW_GLOBS = (
    "visual_editor_component/frontend/js/editor_inspector*.js",
    "visual_editor_component/frontend/styles/editor*.css",
    "ui/style*.py",
)

DEBUG_ALLOWED_SOURCES = frozenset(
    {
        "app_modules/debug_tools.py",
        "ui/input_review_panel.py",
        "ui/diagnostics_panel.py",
        "visual_editor_component/frontend/js/editor_debug_shell.js",
        "visual_editor_component/frontend/js/editor_debug_readiness.js",
        "visual_editor_component/frontend/js/editor_readiness.js",
        "visual_editor_component/frontend/styles/editor_debug.css",
        "ui/style_debug.py",
        "itinerary_generation/input_review.py",
        "pdf_exporter_modules/pdf_internal_review_appendix.py",
    }
)

FORBIDDEN_NORMAL_UI_MARKERS = (
    "Document checks",
    "Export checks",
    "Autosave ready",
    "Server autosave ready",
    "Advanced tools",
    "Structured input review",
    "Rows to review",
    "Parser confidence",
    "Safe parser fixes",
    "Correction queue",
    "Review summary",
    "Client QA",
    "Ready for Client",
    "Needs Review",
    "WHY THIS IMAGE",
    "IMAGE TOOLS",
    "REPLACEMENT IMAGE",
)

HIGH_VALUE_SOURCE_ROOTS = (
    "app_modules",
    "parser_modules",
    "pdf_exporter_modules",
    "images",
    "visual_editor_component/frontend/js",
    "visual_editor_component/frontend/styles",
)

PATCH_HISTORY_NAME_MARKERS = (
    "_late",
    "_corrections",
    "_new",
    "_old",
    "_misc",
    "-late",
    "-corrections",
    "-new",
    "-old",
    "-misc",
)

ROOT_PATCH_ARTIFACT_NAMES = frozenset({"CHANGED_FILES_MANIFEST.md", "DELETION_MANIFEST.md"})
PATCH_METADATA_DIR_NAMES = frozenset({"_patch_metadata"})
DUPLICATE_TEST_DIRS = ("tests", "visual_editor_component/tests")

TOP_LEVEL_COMPATIBILITY_FACADES = {
    "generator.py": 90,
    "image_matcher.py": 40,
    "itinerary_parser.py": 40,
    "normalizer.py": 20,
    "pdf_exporter.py": 100,
    "text_polish.py": 20,
}


CLEANED_GENERATION_CORE_FACADES = {
    "itinerary_generation/day_intro_engine_core.py": 80,
    "itinerary_generation/day_render_blocks_core.py": 80,
    "itinerary_generation/editable_draft_core.py": 120,
    "itinerary_generation/exclusion_sections_core.py": 80,
    "itinerary_generation/nutshell_domain_core.py": 80,
    "itinerary_generation/qa_report_core.py": 80,
    "itinerary_generation/quality_gate_core.py": 140,
    "itinerary_generation/structured_builder_core.py": 160,
    "itinerary_generation/summaries_core.py": 80,
}

GENERATION_CORE_FACADE_MODULES = (
    "itinerary_generation.day_intro_engine_core",
    "itinerary_generation.day_render_blocks_core",
    "itinerary_generation.editable_draft_core",
    "itinerary_generation.exclusion_sections_core",
    "itinerary_generation.nutshell_domain_core",
    "itinerary_generation.qa_report_core",
    "itinerary_generation.quality_gate_core",
    "itinerary_generation.structured_builder_core",
    "itinerary_generation.summaries_core",
)

GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE = (
    "itinerary_generation/city_experience_classifier.py",
    "itinerary_generation/day_intro_activity.py",
    "itinerary_generation/day_intro_arrival.py",
    "itinerary_generation/day_intro_classification.py",
    "itinerary_generation/day_intro_route.py",
    "itinerary_generation/day_render_activity_blocks.py",
    "itinerary_generation/day_render_block_ordering.py",
    "itinerary_generation/day_render_document_adapter.py",
    "itinerary_generation/day_render_group_tour_blocks.py",
    "itinerary_generation/day_render_leisure_blocks.py",
    "itinerary_generation/day_render_transport_blocks.py",
    "itinerary_generation/debug/qa_edit_events.py",
    "itinerary_generation/debug/qa_report_model.py",
    "itinerary_generation/debug/qa_report_persist.py",
    "itinerary_generation/debug/qa_report_render.py",
    "itinerary_generation/debug/qa_warning_events.py",
    "itinerary_generation/editable_draft_model.py",
    "itinerary_generation/editable_draft_normalize.py",
    "itinerary_generation/editable_draft_lookup.py",
    "itinerary_generation/editable_draft_merge.py",
    "itinerary_generation/editable_draft_legacy_bridge.py",
    "itinerary_generation/exclusion_commercial_items.py",
    "itinerary_generation/exclusion_flights.py",
    "itinerary_generation/exclusion_formatting.py",
    "itinerary_generation/exclusion_self_transfers.py",
    "itinerary_generation/generation_quality_gate.py",
    "itinerary_generation/client_output_quality_gate.py",
    "itinerary_generation/journey_arc_builder.py",
    "itinerary_generation/journey_arc_text_safety.py",
    "itinerary_generation/nutshell_detection.py",
    "itinerary_generation/nutshell_journey_builder.py",
    "itinerary_generation/nutshell_labels.py",
    "itinerary_generation/nutshell_model.py",
    "itinerary_generation/nutshell_route_parser.py",
    "itinerary_generation/nutshell_source.py",
    "itinerary_generation/quality_gate_patterns.py",
    "itinerary_generation/structured_row_helpers.py",
    "itinerary_generation/structured_items_builder.py",
    "itinerary_generation/structured_warning_builder.py",
    "itinerary_generation/structured_days_builder.py",
    "itinerary_generation/structured_travel_sequences.py",
    "itinerary_generation/structured_final_sections.py",
    "itinerary_generation/trip_glance_builder.py",
)

EXACT_VAGUE_FILE_NAMES = frozenset({"utils.py", "helpers.py", "utils.js", "helpers.js", "utils.css", "helpers.css"})

PYTHON_FUNCTION_ALLOWLIST = frozenset(
    {
        "itinerary_generation/activity_titles_core.py:create_client_activity_title",
        "itinerary_generation/day_intro_engine.py:create_day_intro",
        "itinerary_generation/summaries.py:describe_city_experience",
    }
)

PYTHON_FILE_ALLOWLIST = frozenset(
    {
        "itinerary_generation/data/nordic_destination_registry.py",
    }
)


def _repo_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_normal_workflow_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for relative in NORMAL_WORKFLOW_SOURCES:
        path = REPO_ROOT / relative
        if path.exists():
            files.append(path)
    for pattern in NORMAL_WORKFLOW_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(pattern)))
    unique = sorted({path.resolve() for path in files})
    return tuple(Path(path) for path in unique if _repo_path(Path(path)) not in DEBUG_ALLOWED_SOURCES)


def forbidden_normal_ui_hits() -> tuple[SourceHit, ...]:
    hits: list[SourceHit] = []
    for path in iter_normal_workflow_files():
        text = _read(path)
        for marker in FORBIDDEN_NORMAL_UI_MARKERS:
            if marker in text:
                hits.append(SourceHit(_repo_path(path), marker))
    return tuple(hits)


def source_contains(path: str, marker: str) -> bool:
    return marker in _read(REPO_ROOT / path)


def _source_files(root: Path, suffixes: frozenset[str]) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in suffixes
            and "__pycache__" not in path.parts
            and ".git" not in path.parts
        )
    )


def oversized_frontend_js_files(limit: int = 500) -> tuple[SizeHit, ...]:
    root = REPO_ROOT / "visual_editor_component/frontend/js"
    return _oversized_files(root, frozenset({".js"}), limit)


def oversized_workflow_python_files(limit: int = 500) -> tuple[SizeHit, ...]:
    root = REPO_ROOT / "app_modules"
    return _oversized_files(root, frozenset({".py"}), limit)


def oversized_core_python_files(limit: int = 700) -> tuple[SizeHit, ...]:
    hits: list[SizeHit] = []
    for relative in ("parser_modules", "itinerary_generation", "pdf_exporter_modules", "images"):
        hits.extend(_oversized_files(REPO_ROOT / relative, frozenset({".py"}), limit))
    return tuple(hit for hit in hits if hit.path not in PYTHON_FILE_ALLOWLIST)


def _oversized_files(root: Path, suffixes: frozenset[str], limit: int) -> tuple[SizeHit, ...]:
    hits: list[SizeHit] = []
    for path in _source_files(root, suffixes):
        line_count = len(_read(path).splitlines())
        if line_count > limit:
            hits.append(SizeHit(_repo_path(path), line_count, limit))
    return tuple(hits)


def oversized_python_functions(limit: int = 200) -> tuple[FunctionHit, ...]:
    hits: list[FunctionHit] = []
    for relative in ("app_modules", "parser_modules", "itinerary_generation", "pdf_exporter_modules", "images"):
        for path in _source_files(REPO_ROOT / relative, frozenset({".py"})):
            try:
                tree = ast.parse(_read(path))
            except SyntaxError:
                continue
            rel_path = _repo_path(path)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if getattr(node, "end_lineno", None) is None:
                    continue
                key = f"{rel_path}:{node.name}"
                if key in PYTHON_FUNCTION_ALLOWLIST:
                    continue
                line_count = int(node.end_lineno) - int(node.lineno) + 1
                if line_count > limit:
                    hits.append(FunctionHit(rel_path, node.name, line_count, limit))
    return tuple(hits)


def patch_history_name_hits() -> tuple[str, ...]:
    hits: list[str] = []
    suffixes = frozenset({".py", ".js", ".css"})
    for relative in HIGH_VALUE_SOURCE_ROOTS:
        for path in _source_files(REPO_ROOT / relative, suffixes):
            name = path.name.lower()
            if name in EXACT_VAGUE_FILE_NAMES or any(marker in name for marker in PATCH_HISTORY_NAME_MARKERS):
                hits.append(_repo_path(path))
    return tuple(sorted(hits))


def import_from_hits(path: str, forbidden_modules: tuple[str, ...]) -> tuple[str, ...]:
    """Return forbidden module-level imports.

    Local imports are allowed for explicit debug/profile gates because they keep
    heavyweight review code out of the normal import path.
    """

    source_path = REPO_ROOT / path
    tree = ast.parse(_read(source_path))
    offenders: list[str] = []
    for node in tree.body:
        module = ""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if _module_matches(module, forbidden_modules):
                    offenders.append(f"{path}:{node.lineno}:{module}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _module_matches(module, forbidden_modules):
                offenders.append(f"{path}:{node.lineno}:{module}")
    return tuple(offenders)


def _module_matches(module: str, forbidden_modules: tuple[str, ...]) -> bool:
    return any(module == forbidden or module.startswith(f"{forbidden}.") for forbidden in forbidden_modules)


def all_import_hits(path: str, forbidden_modules: tuple[str, ...]) -> tuple[str, ...]:
    """Return forbidden imports anywhere in a module, including lazy imports."""

    source_path = REPO_ROOT / path
    tree = ast.parse(_read(source_path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        module = ""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if _module_matches(module, forbidden_modules):
                    offenders.append(f"{path}:{node.lineno}:{module}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _module_matches(module, forbidden_modules):
                offenders.append(f"{path}:{node.lineno}:{module}")
    return tuple(offenders)


def destination_transport_cycle_hits() -> tuple[str, ...]:
    """Return direct imports that would recreate the destination/transport cycle."""

    hits: list[str] = []
    hits.extend(all_import_hits("itinerary_generation/transport_detection.py", ("itinerary_generation.destination_helpers",)))
    return tuple(sorted(hits))


def oversized_editor_css_files(limit: int = 500) -> tuple[SizeHit, ...]:
    root = REPO_ROOT / "visual_editor_component/frontend/styles"
    return _oversized_files(root, frozenset({".css"}), limit)


def oversized_streamlit_style_files(limit: int = 260) -> tuple[SizeHit, ...]:
    """Return Streamlit style modules that have absorbed too many responsibilities."""

    root = REPO_ROOT / "ui"
    return tuple(
        hit
        for hit in _oversized_files(root, frozenset({".py"}), limit)
        if Path(hit.path).name.startswith("style_")
    )


def root_patch_artifact_hits() -> tuple[str, ...]:
    hits = [name for name in ROOT_PATCH_ARTIFACT_NAMES if (REPO_ROOT / name).exists()]
    hits.extend(name for name in PATCH_METADATA_DIR_NAMES if (REPO_ROOT / name).exists())
    return tuple(sorted(hits))


def duplicate_shared_clean_space_hits() -> tuple[str, ...]:
    """Return local clean_space definitions outside the shared text helper.

    The app has many text-heavy layers, but they should import the canonical
    whitespace normalizer instead of each owning a subtly different copy.
    """

    hits: list[str] = []
    for relative in (
        "app_modules",
        "parser_modules",
        "normalizer_modules",
        "itinerary_generation",
        "pdf_exporter_modules",
        "images",
        "text_polish_modules",
    ):
        for path in _source_files(REPO_ROOT / relative, frozenset({".py"})):
            try:
                tree = ast.parse(_read(path))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "clean_space":
                    hits.append(f"{_repo_path(path)}:{node.lineno}")
    return tuple(sorted(hits))


def duplicate_test_path_hits() -> tuple[str, ...]:
    by_name: dict[str, list[str]] = {}
    for relative in DUPLICATE_TEST_DIRS:
        root = REPO_ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("test_*.py"):
            if "__pycache__" in path.parts:
                continue
            by_name.setdefault(path.name, []).append(_repo_path(path))
    return tuple(sorted(path for paths in by_name.values() if len(paths) > 1 for path in paths))


def oversized_core_named_python_files(limit: int = 700) -> tuple[SizeHit, ...]:
    hits: list[SizeHit] = []
    for relative in ("parser_modules", "itinerary_generation", "pdf_exporter_modules", "images"):
        for path in _source_files(REPO_ROOT / relative, frozenset({".py"})):
            if not path.stem.endswith("_core"):
                continue
            line_count = len(_read(path).splitlines())
            if line_count > limit:
                hits.append(SizeHit(_repo_path(path), line_count, limit))
    return tuple(hits)


def oversized_cleaned_generation_core_facades() -> tuple[SizeHit, ...]:
    """Return cleaned generation-core facades that grew back into implementations."""

    hits: list[SizeHit] = []
    for relative, limit in CLEANED_GENERATION_CORE_FACADES.items():
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        line_count = len(_read(path).splitlines())
        if line_count > limit:
            hits.append(SizeHit(relative, line_count, limit))
    return tuple(hits)


def top_level_compatibility_facade_hits() -> tuple[str, ...]:
    """Return top-level compatibility wrappers that grew implementation logic."""

    hits: list[str] = []
    for relative, line_limit in TOP_LEVEL_COMPATIBILITY_FACADES.items():
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        source = _read(path)
        line_count = len(source.splitlines())
        if line_count > line_limit:
            hits.append(f"{relative}: {line_count} lines > limit {line_limit}")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            hits.append(f"{relative}: syntax error: {exc}")
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                hits.append(f"{relative}:{node.lineno}: defines {node.name!r} instead of re-exporting")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ",".join(alias.name for alias in getattr(node, "names", ()))
                imported_from = getattr(node, "module", "") or module
                if _module_matches(imported_from, ("streamlit", "app_modules")):
                    hits.append(f"{relative}:{node.lineno}: imports app/UI runtime module {imported_from!r}")
    return tuple(sorted(hits))


def generation_implementation_core_import_hits() -> tuple[str, ...]:
    """Return named generation implementation modules that still import cleaned core modules."""

    hits: list[str] = []
    for relative in GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE:
        if not (REPO_ROOT / relative).exists():
            continue
        hits.extend(import_from_hits(relative, GENERATION_CORE_FACADE_MODULES))
    return tuple(sorted(hits))


@dataclass(frozen=True)
class ArchitectureCheck:
    name: str
    check: Callable[[], tuple[str, ...]]


def _stringify_hit(hit: object) -> str:
    if isinstance(hit, SourceHit):
        return f"{hit.path}: contains {hit.marker!r}"
    if isinstance(hit, SizeHit):
        return f"{hit.path}: {hit.lines} lines > limit {hit.limit}"
    if isinstance(hit, FunctionHit):
        return f"{hit.path}:{hit.name}: {hit.lines} lines > limit {hit.limit}"
    return str(hit)


def _fail_if_any(label: str, hits: tuple[object, ...]) -> tuple[str, ...]:
    return tuple(f"{label}: {_stringify_hit(hit)}" for hit in hits)


def _debug_review_lazy_load_failures() -> tuple[str, ...]:
    failures: list[str] = []
    failures.extend(
        _fail_if_any(
            "main workflow debug imports must stay lazy",
            import_from_hits("app_modules/main_view.py", ("ui.diagnostics_panel", "ui.input_review_panel")),
        )
    )
    failures.extend(
        _fail_if_any(
            "input review imports must stay lazy",
            import_from_hits("app_modules/generation_messages.py", ("ui.input_review_panel",)),
        )
    )
    failures.extend(
        _fail_if_any(
            "debug diagnostics imports must stay lazy",
            import_from_hits("app_modules/debug_tools.py", ("ui.diagnostics_panel",)),
        )
    )

    required_markers = {
        "app_modules/debug_tools.py": (
            "if not is_debug_mode(st.session_state):",
            "from ui.diagnostics_panel import",
        ),
        "app_modules/generation_messages.py": (
            "if not is_debug_mode(state):",
            "from ui.input_review_panel import",
        ),
    }
    for relative, markers in required_markers.items():
        for marker in markers:
            if not source_contains(relative, marker):
                failures.append(f"debug/review lazy boundary missing in {relative}: {marker!r}")
    return tuple(failures)


def _pdf_internal_review_lazy_load_failures() -> tuple[str, ...]:
    failures = list(
        _fail_if_any(
            "PDF internal review appendix must stay lazily imported",
            import_from_hits(
                "pdf_exporter_modules/typed_exporter.py",
                ("pdf_exporter_modules.pdf_internal_review_appendix",),
            ),
        )
    )
    typed_exporter = _read(REPO_ROOT / "pdf_exporter_modules" / "typed_exporter.py")
    gate = "if profile.include_internal_notes:"
    call = "_render_internal_review_appendix(render_document, story, styles)"
    if gate not in typed_exporter:
        failures.append("PDF internal review appendix gate is missing")
    if call not in typed_exporter:
        failures.append("PDF internal review appendix render call is missing")
    if gate in typed_exporter and call in typed_exporter and typed_exporter.index(gate) > typed_exporter.index(call):
        failures.append("PDF internal review appendix render call is no longer behind its profile gate")
    return tuple(failures)


def _inspector_image_replacement_failures() -> tuple[str, ...]:
    inspector_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "visual_editor_component/frontend/js").glob("editor_inspector*.js")
    )
    forbidden = (
        "renderImageToolOverlay",
        "data-img-action",
        "data-cover-img-action",
        "inspectorImageUploadInput",
        "replacement image",
        "Why this image",
    )
    return tuple(
        f"right inspector must not own canvas image replacement behavior: {marker!r}"
        for marker in forbidden
        if marker in inspector_sources
    )


def _architecture_checks() -> tuple[ArchitectureCheck, ...]:
    return (
        ArchitectureCheck(
            "Normal workflow UI bloat markers",
            lambda: _fail_if_any("normal workflow visible bloat", forbidden_normal_ui_hits()),
        ),
        ArchitectureCheck(
            "Frontend JS file size",
            lambda: _fail_if_any("oversized frontend JS", oversized_frontend_js_files()),
        ),
        ArchitectureCheck(
            "Workflow Python file size",
            lambda: _fail_if_any("oversized workflow Python", oversized_workflow_python_files()),
        ),
        ArchitectureCheck(
            "Core Python file size",
            lambda: _fail_if_any("oversized core Python", oversized_core_python_files()),
        ),
        ArchitectureCheck(
            "Editor CSS file size",
            lambda: _fail_if_any("oversized editor CSS", oversized_editor_css_files()),
        ),
        ArchitectureCheck(
            "Streamlit style module size",
            lambda: _fail_if_any("oversized Streamlit style module", oversized_streamlit_style_files()),
        ),
        ArchitectureCheck(
            "Core-named Python file size",
            lambda: _fail_if_any("oversized *_core Python", oversized_core_named_python_files()),
        ),
        ArchitectureCheck(
            "Cleaned generation facade size",
            lambda: _fail_if_any("cleaned facade grew back", oversized_cleaned_generation_core_facades()),
        ),
        ArchitectureCheck(
            "Python function size",
            lambda: _fail_if_any("oversized Python function", oversized_python_functions()),
        ),
        ArchitectureCheck(
            "Patch-history and vague source names",
            lambda: _fail_if_any("bad high-value source name", patch_history_name_hits()),
        ),
        ArchitectureCheck("Debug/review lazy loading", _debug_review_lazy_load_failures),
        ArchitectureCheck("PDF internal review lazy loading", _pdf_internal_review_lazy_load_failures),
        ArchitectureCheck("Right inspector scope", _inspector_image_replacement_failures),
        ArchitectureCheck(
            "Root patch artifacts",
            lambda: _fail_if_any("root patch artifact", root_patch_artifact_hits()),
        ),
        ArchitectureCheck(
            "Duplicate test module names",
            lambda: _fail_if_any("duplicate test module", duplicate_test_path_hits()),
        ),
        ArchitectureCheck(
            "Shared clean_space ownership",
            lambda: _fail_if_any("duplicate clean_space definition", duplicate_shared_clean_space_hits()),
        ),
        ArchitectureCheck(
            "Top-level compatibility facade scope",
            lambda: _fail_if_any("compatibility facade grew implementation logic", top_level_compatibility_facade_hits()),
        ),
        ArchitectureCheck(
            "Destination/transport import cycle",
            lambda: _fail_if_any("destination transport cycle", destination_transport_cycle_hits()),
        ),
        ArchitectureCheck(
            "Generation core facade dependency direction",
            lambda: _fail_if_any(
                "implementation imports cleaned core facade",
                generation_implementation_core_import_hits(),
            ),
        ),
    )


def run_architecture_checks() -> tuple[str, ...]:
    failures: list[str] = []
    for check in _architecture_checks():
        check_failures = check.check()
        failures.extend(f"{check.name}: {failure}" for failure in check_failures)
    return tuple(failures)


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    failures = run_architecture_checks()
    if not failures:
        print("Architecture guards passed.")
        return 0

    print("Architecture guards failed:", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
