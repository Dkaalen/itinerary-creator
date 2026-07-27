"""Deterministic repository fingerprints for generated architecture reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ReportFingerprint:
    """Repository and audited-source identity captured with one report."""

    repository_head: str
    repository_head_tree: str
    working_tree_clean: bool
    python_source_tree_sha256: str
    python_source_file_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _git_value(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", "-c", "safe.directory=*", *args),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip()


def python_source_tree_fingerprint(root: Path, paths: Iterable[Path]) -> tuple[str, int]:
    """Hash the exact Python source inputs used by an architecture audit."""

    digest = sha256()
    count = 0
    for path in sorted({Path(item).resolve() for item in paths}):
        if not path.is_file():
            continue
        relative = path.relative_to(root.resolve()).as_posix()
        content = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
        digest.update(b"\0")
        count += 1
    return f"sha256:{digest.hexdigest()}", count


def build_report_fingerprint(root: Path, paths: Iterable[Path]) -> ReportFingerprint:
    """Return commit, committed-tree, dirty-state, and audited-source identity."""

    source_hash, source_count = python_source_tree_fingerprint(root, paths)
    repository_head = _git_value(root, "rev-parse", "HEAD")
    repository_head_tree = _git_value(root, "rev-parse", "HEAD^{tree}")
    status = _git_value(root, "status", "--porcelain", "--untracked-files=no")
    return ReportFingerprint(
        repository_head=repository_head,
        repository_head_tree=repository_head_tree,
        # A source-only extraction has no Git metadata, so cleanliness cannot
        # be proven there. The audited source hash remains portable.
        working_tree_clean=bool(repository_head and repository_head_tree) and not bool(status),
        python_source_tree_sha256=source_hash,
        python_source_file_count=source_count,
    )


__all__ = [
    "ReportFingerprint",
    "build_report_fingerprint",
    "python_source_tree_fingerprint",
]
