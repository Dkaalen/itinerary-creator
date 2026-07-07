"""Explicit static-contract helpers for tests that must inspect source assets.

Prefer behavior tests for product logic.  Use these helpers only for lightweight
architecture, wiring, and frontend-asset contracts where executing the full UI or
browser runtime would be slower or less reliable than a focused static guard.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative_path: str | Path) -> Path:
    path = Path(relative_path)
    return path if path.is_absolute() else REPO_ROOT / path


@lru_cache(maxsize=None)
def read_contract_text(relative_path: str | Path) -> str:
    """Read a repo file for an explicit static contract test."""

    return repo_path(relative_path).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def python_tree(relative_path: str | Path) -> ast.Module:
    return ast.parse(read_contract_text(relative_path), filename=str(repo_path(relative_path)))


def python_string_constants(relative_path: str | Path) -> tuple[str, ...]:
    return tuple(
        node.value
        for node in ast.walk(python_tree(relative_path))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def python_function_names(relative_path: str | Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(python_tree(relative_path))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def python_class_names(relative_path: str | Path) -> set[str]:
    return {node.name for node in ast.walk(python_tree(relative_path)) if isinstance(node, ast.ClassDef)}


def python_names(relative_path: str | Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(python_tree(relative_path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def python_call_names(relative_path: str | Path) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(python_tree(relative_path)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            calls.add(func.id)
        elif isinstance(func, ast.Attribute):
            calls.add(func.attr)
    return calls


def python_qualified_calls(relative_path: str | Path) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(python_tree(relative_path)):
        if not isinstance(node, ast.Call):
            continue
        parts: list[str] = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        if parts:
            calls.add(".".join(reversed(parts)))
    return calls


def python_imported_names(relative_path: str | Path) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(python_tree(relative_path)):
        if isinstance(node, ast.Import):
            imports.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.update(alias.asname or alias.name for alias in node.names)
    return imports


def assert_contains_all(container: Iterable[str], expected: Iterable[str]) -> None:
    values = set(container)
    missing = sorted(item for item in expected if item not in values)
    assert not missing, f"Missing expected contract values: {missing}"


def assert_excludes_all(container: Iterable[str], forbidden: Iterable[str]) -> None:
    values = set(container)
    present = sorted(item for item in forbidden if item in values)
    assert not present, f"Forbidden contract values are still present: {present}"
