"""Build the standard clean ZIP for ChatGPT handoff.

Use this instead of manually compressing the working tree.  It delegates to the
shared clean-ZIP builder so handoff packages exclude Git metadata, caches,
generated outputs, old ZIP files and local credentials while preserving source
files and safe examples.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_clean_zip import build_clean_zip  # noqa: E402


def default_handoff_output_path(root: str | Path) -> Path:
    """Return the default official handoff ZIP path for *root*."""

    root_path = Path(root).resolve()
    return root_path.parent / f"{root_path.name}-handoff.zip"


def build_handoff_zip(root: str | Path = REPO_ROOT, output: str | Path | None = None) -> tuple[Path, int]:
    """Create the official clean handoff ZIP and return ``(zip_path, file_count)``."""

    root_path = Path(root).resolve()
    output_path = Path(output).resolve() if output is not None else default_handoff_output_path(root_path)
    return build_clean_zip(root_path, output_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the standard clean handoff ZIP without Git metadata, caches, outputs or local secrets."
    )
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Project root to package. Defaults to the repository containing this script.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output ZIP path. Defaults to '<project-folder>-handoff.zip' beside the project root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    zip_path, file_count = build_handoff_zip(args.root, args.output)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Created handoff ZIP: {zip_path} ({file_count} files, {size_mb:.1f} MB)")
    print("Upload this ZIP for ChatGPT code health checks and future patch work.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
