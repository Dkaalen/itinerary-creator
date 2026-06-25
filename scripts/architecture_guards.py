"""Source-level architecture guard helpers for the Itinerary App.

The tests use this module to keep the normal PDF-producing workflow clean while
allowing debug/review code to remain in explicit debug modules.
"""

from __future__ import annotations

import ast
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

EXACT_VAGUE_FILE_NAMES = frozenset({"utils.py", "helpers.py", "utils.js", "helpers.js", "utils.css", "helpers.css"})

PYTHON_FUNCTION_ALLOWLIST = frozenset(
    {
        "itinerary_generation/activity_titles_core.py:create_client_activity_title",
        "itinerary_generation/day_intro_engine_core.py:create_day_intro",
        "itinerary_generation/summaries_core.py:describe_city_experience",
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


def oversized_editor_css_files(limit: int = 500) -> tuple[SizeHit, ...]:
    root = REPO_ROOT / "visual_editor_component/frontend/styles"
    return _oversized_files(root, frozenset({".css"}), limit)


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
