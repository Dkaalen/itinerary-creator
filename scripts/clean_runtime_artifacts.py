"""Remove local runtime/cache artifacts from a checkout.

This is intentionally conservative: it only removes folders/files that are
excluded from clean ZIPs and never touches source files.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GENERATED_DIR_NAMES = {
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".runtime_image_bank",
    "__pycache__",
    "outputs",
    "persistent_drafts",
    "qa_reports",
}
GENERATED_SUFFIXES = (".pyc", ".pyo")
EMPTY_LEGACY_DIRS = (
    Path("visual_editor_component/app_modules"),
    Path("visual_editor_component/ui"),
)


def clean_runtime_artifacts(root: str | Path = REPO_ROOT, *, dry_run: bool = False) -> list[Path]:
    """Remove known generated artifacts and return paths that were/would be removed."""

    root_path = Path(root).resolve()
    removed: list[Path] = []

    for path in sorted(root_path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if ".git" in path.parts:
            continue
        relative = path.relative_to(root_path)
        should_remove = False
        if path.is_dir() and path.name in GENERATED_DIR_NAMES:
            should_remove = True
        elif path.is_file() and path.name.endswith(GENERATED_SUFFIXES):
            should_remove = True
        elif path.is_file() and path.name == ".chatgpt_write_test.txt":
            should_remove = True
        elif path.is_dir() and relative in EMPTY_LEGACY_DIRS and not any(path.iterdir()):
            should_remove = True

        if not should_remove:
            continue
        removed.append(relative)
        if dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)

    return sorted(removed, key=lambda value: value.as_posix())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove generated runtime/cache artifacts from the project tree.")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Project root to clean.")
    parser.add_argument("--dry-run", action="store_true", help="List paths without deleting them.")
    args = parser.parse_args(argv)

    removed = clean_runtime_artifacts(args.root, dry_run=args.dry_run)
    action = "Would remove" if args.dry_run else "Removed"
    print(f"{action} {len(removed)} runtime artifact path(s).")
    for path in removed:
        print(path.as_posix())
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
