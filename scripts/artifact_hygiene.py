"""Shared artifact hygiene helpers for patch/project ZIP packaging.

Patch ZIPs should contain source changes only.  Keep Git metadata, Python
bytecode, pytest caches, runtime image-bank clones and other local by-products
out of deliverables so applying a patch does not pollute the user's checkout.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Sequence

ARTIFACT_EXCLUDED_DIRS = frozenset({
    ".cache",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".runtime_image_bank",
    "__pycache__",
    "_patch_metadata",
    ".venv",
    "venv",
    "outputs",
    "persistent_drafts",
    "qa_reports",
})

ARTIFACT_EXCLUDED_FILENAMES = frozenset({
    ".chatgpt_write_test.txt",
    "CHANGED_FILES_MANIFEST.md",
    "DELETION_MANIFEST.md",
    ".DS_Store",
    "credentials.json",
    "gcp-service-account.json",
    "google-service-account.json",
    "secrets.toml",
    "service-account.json",
    "service_account.json",
})

ARTIFACT_EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".zip", ".tmp", ".bak")
ENV_EXAMPLE_FILENAMES = frozenset({".env.example", ".env.sample", ".env.template"})
EMPTY_LEGACY_DIRS = (
    Path("visual_editor_component/app_modules"),
    Path("visual_editor_component/ui"),
)

SENSITIVE_ARTIFACT_TEXT_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
)


def is_artifact_noise_path(path: str | Path) -> bool:
    """Return True when *path* is local/generated noise, not patch content."""

    candidate = Path(path)
    parts = set(candidate.parts)
    if parts & ARTIFACT_EXCLUDED_DIRS:
        return True
    if candidate.name in ARTIFACT_EXCLUDED_FILENAMES:
        return True
    if _is_local_env_file(candidate):
        return True
    return candidate.name.endswith(ARTIFACT_EXCLUDED_SUFFIXES)


def _is_local_env_file(path: Path) -> bool:
    """Return True for local dotenv files while preserving shareable examples."""

    name = path.name
    return name.startswith(".env") and name not in ENV_EXAMPLE_FILENAMES


def iter_clean_artifact_files(root: str | Path) -> Iterator[Path]:
    """Yield source files under *root*, pruning generated/runtime folders early."""

    root_path = Path(root)
    clean_files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root_path):
        current = Path(current_root)
        relative_current = current.relative_to(root_path)
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if not is_artifact_noise_path(relative_current / dirname)
        )
        for filename in filenames:
            path = current / filename
            relative = path.relative_to(root_path)
            if not is_artifact_noise_path(relative):
                clean_files.append(path)

    yield from sorted(clean_files, key=lambda path: path.relative_to(root_path).as_posix())


def sensitive_artifact_text_hits(text: str, markers: Sequence[str] = SENSITIVE_ARTIFACT_TEXT_MARKERS) -> tuple[str, ...]:
    """Return sensitive credential markers found in shareable artifact text.

    File-name rules catch normal local secret files. This content-level guard is
    a second line of defence for accidental credential material pasted into a
    differently named source file or bundled into a manually-created ZIP.
    """

    return tuple(marker for marker in markers if marker in text)

def read_text_safely(data: bytes, *, limit: int = 2_000_000) -> str:
    """Return UTF-8 text for small archive members, otherwise an empty string."""

    if len(data) > limit:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""
