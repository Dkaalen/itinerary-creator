"""Build a conservative handover list of deletion candidates.

This tool is read-only. It does not delete files. It records files that look like
cleanup candidates because static imports no longer prove active ownership.
Every listed path still needs a dedicated deletion patch with targeted tests.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_legacy_facades import audit_modules
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
REQUIRED_PUBLIC_SURFACES = {
    "generator.py",
    "image_matcher.py",
    "itinerary_parser.py",
    "normalizer.py",
    "pdf_exporter.py",
    "text_polish.py",
    "itinerary_generation/public_api.py",
    "pdf_exporter_modules/public_api.py",
}
PACKAGE_INIT_BASENAME = "__init__.py"
SCRIPT_ENTRYPOINT_ROOT = "scripts/"


@dataclass(frozen=True)
class DeletionCandidate:
    path: str
    reason: str
    static_importers: tuple[str, ...]
    safety_note: str


@dataclass(frozen=True)
class DeletionCandidateReport:
    candidates: tuple[DeletionCandidate, ...]
    held_back: tuple[DeletionCandidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidates": [asdict(item) for item in self.candidates],
            "held_back": [asdict(item) for item in self.held_back],
        }


def iter_python_files(root: Path = ROOT) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if not any(part in EXCLUDED_PARTS for part in path.parts)
        )
    )


def _module_name(path: Path, root: Path = ROOT) -> str:
    return path.relative_to(root).with_suffix("").as_posix().replace("/", ".")


def _imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _import_map(all_files: tuple[Path, ...], root: Path = ROOT) -> dict[Path, set[str]]:
    return {path: _imports(path) for path in all_files}


def _static_importers(
    target: Path,
    imports_by_file: dict[Path, set[str]],
    root: Path = ROOT,
) -> tuple[str, ...]:
    module = _module_name(target, root)
    importers: list[str] = []
    for path, imported_modules in imports_by_file.items():
        if path == target:
            continue
        if module in imported_modules or any(imported.startswith(module + ".") for imported in imported_modules):
            importers.append(path.relative_to(root).as_posix())
    return tuple(sorted(importers))


def _is_required_public_surface(path: str) -> bool:
    return path in REQUIRED_PUBLIC_SURFACES or path.endswith("/public_api.py")


def _should_hold_back(path: str, importers: tuple[str, ...]) -> str | None:
    if Path(path).name == PACKAGE_INIT_BASENAME:
        return "package initializer; never delete from static import evidence alone"
    if _is_required_public_surface(path):
        return "documented public compatibility surface"
    if path.startswith(SCRIPT_ENTRYPOINT_ROOT):
        return "script entrypoint; verify CLI/backwards compatibility before deletion"
    if importers:
        return "still has static importers"
    return None


def build_report(root: Path = ROOT) -> DeletionCandidateReport:
    all_files = iter_python_files(root)
    imports_by_file = _import_map(all_files, root)
    module_audit = audit_modules()
    candidates: list[DeletionCandidate] = []
    held_back: list[DeletionCandidate] = []
    for item in module_audit:
        if not item.is_facade and item.production_importers:
            continue
        path = item.path
        target = root / path
        if not target.exists():
            continue
        importers = _static_importers(target, imports_by_file, root)
        if item.is_facade and not item.production_importers:
            reason = "facade-like module with zero production importers"
            note = _should_hold_back(path, importers)
        elif not item.production_importers:
            reason = "module with zero production importers"
            note = "not facade-like; review for dynamic/data ownership before deletion"
        else:
            reason = "facade-like module with production importers"
            note = _should_hold_back(path, importers)
        finding = DeletionCandidate(
            path=path,
            reason=reason,
            static_importers=importers,
            safety_note=note or "candidate for a dedicated deletion patch after targeted validation",
        )
        if note:
            held_back.append(finding)
        else:
            candidates.append(finding)
    return DeletionCandidateReport(
        candidates=tuple(sorted(candidates, key=lambda item: item.path)),
        held_back=tuple(sorted(held_back, key=lambda item: item.path)),
    )


def write_markdown(report: DeletionCandidateReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Deletion Candidate Handover List",
        "",
        "Generated by `scripts/deletion_candidate_audit.py`.",
        "",
        "This is a handover list only. Do not delete all entries in one patch.",
        "Each candidate needs an import-search proof, targeted tests, and a separate deletion commit.",
        "",
        f"Immediate candidates: {len(report.candidates)}",
        f"Held back for compatibility/safety: {len(report.held_back)}",
        "",
        "## Immediate candidates",
        "",
        "| File | Reason | Importers | Safety note |",
        "|---|---|---:|---|",
    ]
    for item in report.candidates:
        lines.append(
            f"| `{item.path}` | {item.reason} | {len(item.static_importers)} | {item.safety_note} |"
        )
    if not report.candidates:
        lines.append("| — | — | — | — |")
    lines.extend([
        "",
        "## Held back",
        "",
        "| File | Reason | Importers | Safety note |",
        "|---|---|---:|---|",
    ])
    for item in report.held_back:
        lines.append(
            f"| `{item.path}` | {item.reason} | {len(item.static_importers)} | {item.safety_note} |"
        )
    if not report.held_back:
        lines.append("| — | — | — | — |")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=ROOT / "docs/reports/deletion_candidates/latest.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "docs/reports/deletion_candidates/latest.md")
    args = parser.parse_args()
    report = build_report()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")
    print(f"candidates={len(report.candidates)} held_back={len(report.held_back)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
