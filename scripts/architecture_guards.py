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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from scripts.architecture_guard_models import FunctionHit, SizeHit, SourceHit
from scripts.architecture_guard_size_checks import (
    _source_files,
    oversized_cleaned_generation_core_facades,
    oversized_core_named_python_files,
    oversized_core_python_files,
    oversized_editor_css_files,
    oversized_frontend_js_files,
    oversized_python_functions,
    oversized_streamlit_style_files,
    oversized_workflow_python_files,
    top_level_compatibility_facade_hits,
)

from scripts.architecture_guard_config import (
    CLEANED_GENERATION_CORE_FACADES,
    DEBUG_ALLOWED_SOURCES,
    DUPLICATE_TEST_DIRS,
    EXACT_VAGUE_FILE_NAMES,
    FORBIDDEN_NORMAL_UI_MARKERS,
    GENERATION_CORE_FACADE_MODULES,
    GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE,
    HIGH_VALUE_SOURCE_ROOTS,
    NORMAL_WORKFLOW_GLOBS,
    NORMAL_WORKFLOW_SOURCES,
    PATCH_HISTORY_NAME_MARKERS,
    PATCH_METADATA_DIR_NAMES,
    PYTHON_FILE_ALLOWLIST,
    PYTHON_FUNCTION_ALLOWLIST,
    ROOT_PATCH_ARTIFACT_NAMES,
    TOP_LEVEL_COMPATIBILITY_FACADES,
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
