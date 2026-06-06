"""Build a clean source ZIP for ChatGPT handoff or lightweight backups.

The normal project checkout can contain Git metadata, caches, generated PDFs,
old patch ZIPs and other local by-products.  This script packages only source
files that are safe to share, using the same artifact hygiene rules as patch
packaging tests.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.artifact_hygiene import iter_clean_artifact_files  # noqa: E402


def _default_output_path(root: Path) -> Path:
    return root.parent / f"{root.name}-clean.zip"


def build_clean_zip(root: str | Path, output: str | Path | None = None) -> tuple[Path, int]:
    """Create a clean source ZIP and return ``(zip_path, file_count)``.

    Git metadata, Python/pytest caches, generated outputs and existing ZIP files
    are excluded through :func:`scripts.artifact_hygiene.iter_clean_artifact_files`.
    """

    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise FileNotFoundError(f"Project root does not exist or is not a directory: {root_path}")

    output_path = Path(output).resolve() if output is not None else _default_output_path(root_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = tuple(iter_clean_artifact_files(root_path))
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root_path).as_posix())

    return output_path, len(files)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a clean project ZIP without Git metadata, caches, outputs or old ZIP files."
    )
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Project root to package. Defaults to the repository containing this script.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output ZIP path. Defaults to '<project-folder>-clean.zip' beside the project root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    zip_path, file_count = build_clean_zip(args.root, args.output)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Created {zip_path} ({file_count} files, {size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
