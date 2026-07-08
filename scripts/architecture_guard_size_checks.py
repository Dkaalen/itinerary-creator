"""File and function size checks for architecture guards."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.architecture_guard_config import (
    CLEANED_GENERATION_CORE_FACADES,
    PYTHON_FILE_ALLOWLIST,
    PYTHON_FUNCTION_ALLOWLIST,
    TOP_LEVEL_COMPATIBILITY_FACADES,
)
from scripts.architecture_guard_models import FunctionHit, SizeHit


def _repo_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_matches(module: str, forbidden_modules: tuple[str, ...]) -> bool:
    return any(module == forbidden or module.startswith(f"{forbidden}.") for forbidden in forbidden_modules)

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
