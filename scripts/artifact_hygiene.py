"""Shared artifact hygiene helpers for patch/project ZIP packaging.

Patch ZIPs should contain source changes only.  Keep Git metadata, Python
bytecode, pytest caches, runtime image-bank clones and other local by-products
out of deliverables so applying a patch does not pollute the user's checkout.
"""

from __future__ import annotations

from pathlib import Path

ARTIFACT_EXCLUDED_DIRS = frozenset({
    ".cache",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".runtime_image_bank",
    "__pycache__",
    ".venv",
    "venv",
    "outputs",
    "persistent_drafts",
    "qa_reports",
})

ARTIFACT_EXCLUDED_FILENAMES = frozenset({
    ".chatgpt_write_test.txt",
    ".DS_Store",
})

ARTIFACT_EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".zip", ".tmp", ".bak")


def is_artifact_noise_path(path: str | Path) -> bool:
    """Return True when *path* is local/generated noise, not patch content."""

    candidate = Path(path)
    parts = set(candidate.parts)
    if parts & ARTIFACT_EXCLUDED_DIRS:
        return True
    if candidate.name in ARTIFACT_EXCLUDED_FILENAMES:
        return True
    return candidate.name.endswith(ARTIFACT_EXCLUDED_SUFFIXES)


def iter_clean_artifact_files(root: str | Path):
    """Yield files under *root* that are safe to include in a source ZIP."""

    root_path = Path(root)
    for path in sorted(root_path.rglob("*")):
        relative = path.relative_to(root_path)
        if is_artifact_noise_path(relative):
            if path.is_dir():
                # rglob cannot be pruned here, but this keeps the predicate in
                # one place and is fast enough for the current project size.
                continue
            continue
        if path.is_file():
            yield path
