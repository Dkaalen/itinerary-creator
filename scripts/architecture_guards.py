"""Source-level architecture guard helpers for the Itinerary App."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.architecture_guard_models import FunctionHit, SizeHit, SourceHit
from scripts.architecture_guard_size_checks import (
    compressed_python_statement_hits,
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
from scripts.architecture_guard_source_checks import (
    _read,
    all_import_hits,
    destination_transport_cycle_hits,
    duplicate_shared_clean_space_hits,
    duplicate_test_path_hits,
    forbidden_normal_ui_hits,
    generation_implementation_core_import_hits,
    import_from_hits,
    itinerary_domain_generation_import_hits,
    iter_normal_workflow_files,
    patch_history_name_hits,
    root_patch_artifact_hits,
    source_contains,
)


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
        ArchitectureCheck("Frontend JS file size", lambda: _fail_if_any("oversized frontend JS", oversized_frontend_js_files())),
        ArchitectureCheck("Workflow Python file size", lambda: _fail_if_any("oversized workflow Python", oversized_workflow_python_files())),
        ArchitectureCheck("Core Python file size", lambda: _fail_if_any("oversized core Python", oversized_core_python_files())),
        ArchitectureCheck("Editor CSS file size", lambda: _fail_if_any("oversized editor CSS", oversized_editor_css_files())),
        ArchitectureCheck("Streamlit style module size", lambda: _fail_if_any("oversized Streamlit style module", oversized_streamlit_style_files())),
        ArchitectureCheck("Core-named Python file size", lambda: _fail_if_any("oversized *_core Python", oversized_core_named_python_files())),
        ArchitectureCheck("Cleaned generation facade size", lambda: _fail_if_any("cleaned facade grew back", oversized_cleaned_generation_core_facades())),
        ArchitectureCheck("Python function size", lambda: _fail_if_any("oversized Python function", oversized_python_functions())),
        ArchitectureCheck(
            "Python statement compression",
            lambda: _fail_if_any("compressed Python statements", compressed_python_statement_hits()),
        ),
        ArchitectureCheck("Patch-history and vague source names", lambda: _fail_if_any("bad high-value source name", patch_history_name_hits())),
        ArchitectureCheck("Debug/review lazy loading", _debug_review_lazy_load_failures),
        ArchitectureCheck("PDF internal review lazy loading", _pdf_internal_review_lazy_load_failures),
        ArchitectureCheck("Right inspector scope", _inspector_image_replacement_failures),
        ArchitectureCheck("Root patch artifacts", lambda: _fail_if_any("root patch artifact", root_patch_artifact_hits())),
        ArchitectureCheck("Duplicate test module names", lambda: _fail_if_any("duplicate test module", duplicate_test_path_hits())),
        ArchitectureCheck("Shared clean_space ownership", lambda: _fail_if_any("duplicate clean_space definition", duplicate_shared_clean_space_hits())),
        ArchitectureCheck("Top-level compatibility facade scope", lambda: _fail_if_any("compatibility facade grew implementation logic", top_level_compatibility_facade_hits())),
        ArchitectureCheck("Destination/transport import cycle", lambda: _fail_if_any("destination transport cycle", destination_transport_cycle_hits())),
        ArchitectureCheck("Neutral domain dependency direction", lambda: _fail_if_any("neutral domain imports generation", itinerary_domain_generation_import_hits())),
        ArchitectureCheck(
            "Generation core facade dependency direction",
            lambda: _fail_if_any("implementation imports cleaned core facade", generation_implementation_core_import_hits()),
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
