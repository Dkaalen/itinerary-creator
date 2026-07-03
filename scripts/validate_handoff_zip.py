"""Validate that a handoff ZIP is safe to share and apply.

This is a preflight guard for accidentally-created manual ZIPs. The official
handoff package should be produced with ``scripts/build_handoff_zip.py``; this
validator catches common mistakes such as bundled Git metadata, bytecode caches,
old ZIP files, local secrets, and credential-like text inside included files.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.artifact_hygiene import (  # noqa: E402
    is_artifact_noise_path,
    read_text_safely,
    sensitive_artifact_text_hits,
)


@dataclass(frozen=True)
class HandoffZipIssue:
    """One unsafe member or content finding inside a handoff ZIP."""

    member: str
    reason: str


def validate_handoff_zip(zip_path: str | Path) -> tuple[HandoffZipIssue, ...]:
    """Return safety issues found in *zip_path*.

    The function is intentionally conservative. A shareable handoff ZIP should
    contain source files only, so any artifact-hygiene match or credential-like
    text is reported.
    """

    path = Path(zip_path)
    issues: list[HandoffZipIssue] = []
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            member_name = _normal_member_name(member.filename)
            if not member_name or member.is_dir():
                continue
            if is_artifact_noise_path(member_name):
                issues.append(HandoffZipIssue(member_name, "excluded artifact/noise path"))
                continue
            if _content_scan_is_exempt(member_name):
                continue
            data = archive.read(member)
            text = read_text_safely(data)
            for marker in sensitive_artifact_text_hits(text):
                issues.append(HandoffZipIssue(member_name, f"sensitive text marker: {marker}"))
    return tuple(issues)


def _content_scan_is_exempt(member_name: str) -> bool:
    """Return True for source/example files that intentionally name secret markers."""

    path = PurePosixPath(member_name)
    name = path.name.casefold()
    parts = tuple(part.casefold() for part in path.parts)
    if "tests" in parts or "scripts" in parts or "docs" in parts:
        return True
    if name in {"readme.md", "secrets.example.toml"}:
        return True
    if ".example." in name or name.endswith(".example"):
        return True
    return False


def _normal_member_name(name: str) -> str:
    """Return a normalized POSIX archive member name without root prefixes."""

    pure = PurePosixPath(name.replace("\\", "/"))
    parts = tuple(part for part in pure.parts if part not in {"", "."})
    return PurePosixPath(*parts).as_posix() if parts else ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a source-only handoff ZIP before sharing or applying it.")
    parser.add_argument("zip_path", help="Path to the handoff ZIP to inspect.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    issues = validate_handoff_zip(args.zip_path)
    if not issues:
        print("Handoff ZIP validation passed.")
        return 0
    print("Handoff ZIP validation failed:")
    for issue in issues:
        print(f"- {issue.member}: {issue.reason}")
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
