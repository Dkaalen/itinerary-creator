"""Source scanning checks used by architecture_guards."""

from __future__ import annotations

import ast
from pathlib import Path

from scripts.architecture_guard_config import (
    DEBUG_ALLOWED_SOURCES,
    DUPLICATE_TEST_DIRS,
    EXACT_VAGUE_FILE_NAMES,
    FILES_THAT_MUST_STAY_DISTINCT,
    FORBIDDEN_NORMAL_UI_MARKERS,
    GENERATION_CORE_FACADE_MODULES,
    GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE,
    HIGH_VALUE_SOURCE_ROOTS,
    NORMAL_WORKFLOW_GLOBS,
    NORMAL_WORKFLOW_SOURCES,
    PATCH_HISTORY_NAME_MARKERS,
    PATCH_METADATA_DIR_NAMES,
    ROOT_PATCH_ARTIFACT_NAMES,
)
from scripts.architecture_guard_models import SourceHit
from scripts.architecture_guard_size_checks import _source_files

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _module_matches(module: str, forbidden_modules: tuple[str, ...]) -> bool:
    return any(module == forbidden or module.startswith(f"{forbidden}.") for forbidden in forbidden_modules)


def import_from_hits(path: str, forbidden_modules: tuple[str, ...]) -> tuple[str, ...]:
    """Return forbidden module-level imports."""

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
    """Return local clean_space definitions outside the shared text helper."""

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


def accidental_file_alias_hits() -> tuple[str, ...]:
    """Return public/root files that were replaced by unrelated nested files."""

    hits: list[str] = []
    for public_relative, nested_relative in FILES_THAT_MUST_STAY_DISTINCT:
        public_path = REPO_ROOT / public_relative
        nested_path = REPO_ROOT / nested_relative
        if not public_path.exists():
            hits.append(f"{public_relative}: missing")
            continue
        if not nested_path.exists():
            hits.append(f"{nested_relative}: missing comparison source")
            continue
        if public_path.read_bytes() == nested_path.read_bytes():
            hits.append(f"{public_relative} duplicates {nested_relative}")
    return tuple(hits)


def generation_implementation_core_import_hits() -> tuple[str, ...]:
    """Return named generation implementation modules that still import cleaned core modules."""

    hits: list[str] = []
    for relative in GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE:
        if not (REPO_ROOT / relative).exists():
            continue
        hits.extend(import_from_hits(relative, GENERATION_CORE_FACADE_MODULES))
    return tuple(sorted(hits))


def itinerary_domain_generation_import_hits() -> tuple[str, ...]:
    """Return neutral-domain modules that depend back on generation code."""

    hits: list[str] = []
    domain_root = REPO_ROOT / "itinerary_domain"
    if not domain_root.exists():
        return ("itinerary_domain package is missing",)
    for path in _source_files(domain_root, frozenset({".py"})):
        relative = path.relative_to(REPO_ROOT).as_posix()
        hits.extend(all_import_hits(relative, ("itinerary_generation",)))
    return tuple(sorted(hits))
