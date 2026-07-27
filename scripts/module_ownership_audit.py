"""Audit overworked modules, facade drift and duplicate-rule hotspots.

This is a read-only developer tool.  It intentionally does not delete files;
it produces evidence for safe cleanup patches.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_fingerprints import ReportFingerprint, build_report_fingerprint
DEFAULT_EXCLUDES = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}


@dataclass(frozen=True)
class FunctionFinding:
    file: str
    name: str
    line_count: int
    start_line: int


@dataclass(frozen=True)
class FileFinding:
    file: str
    line_count: int
    concern: str


@dataclass(frozen=True)
class OwnershipAudit:
    overworked_files: tuple[FileFinding, ...]
    long_functions: tuple[FunctionFinding, ...]
    facade_like_modules: tuple[FileFinding, ...]
    duplicate_rule_hotspots: tuple[FileFinding, ...]
    facade_importers: dict[str, tuple[str, ...]]

    def to_dict(self) -> dict[str, object]:
        return {
            "overworked_files": [asdict(item) for item in self.overworked_files],
            "long_functions": [asdict(item) for item in self.long_functions],
            "facade_like_modules": [asdict(item) for item in self.facade_like_modules],
            "duplicate_rule_hotspots": [asdict(item) for item in self.duplicate_rule_hotspots],
            "facade_importers": {key: list(value) for key, value in self.facade_importers.items()},
        }


def iter_python_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def run_audit(root: Path = ROOT, *, file_line_limit: int = 450, function_line_limit: int = 120) -> OwnershipAudit:
    overworked: list[FileFinding] = []
    long_functions: list[FunctionFinding] = []
    facades: list[FileFinding] = []
    duplicate_hotspots: list[FileFinding] = []
    for path in iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        line_count = len(lines)
        if line_count >= file_line_limit:
            overworked.append(FileFinding(rel, line_count, "large_module"))
        if _looks_like_facade(text):
            facades.append(FileFinding(rel, line_count, "facade_like_module"))
        if _looks_like_duplicate_rule_hotspot(rel, text):
            duplicate_hotspots.append(FileFinding(rel, line_count, "inline_regex_or_replacement_rules"))
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
                function_lines = int(node.end_lineno or node.lineno) - int(node.lineno) + 1
                if function_lines >= function_line_limit:
                    long_functions.append(FunctionFinding(rel, node.name, function_lines, int(node.lineno)))
    sorted_facades = tuple(sorted(facades, key=lambda item: (item.file)))
    return OwnershipAudit(
        overworked_files=tuple(sorted(overworked, key=lambda item: (-item.line_count, item.file))),
        long_functions=tuple(sorted(long_functions, key=lambda item: (-item.line_count, item.file, item.name))),
        facade_like_modules=sorted_facades,
        duplicate_rule_hotspots=tuple(sorted(duplicate_hotspots, key=lambda item: (-item.line_count, item.file))),
        facade_importers=_facade_importers(root, sorted_facades),
    )


def _module_name_for_rel(rel: str) -> str:
    return rel.removesuffix(".py").replace("/", ".")


def _facade_importers(root: Path, facades: tuple[FileFinding, ...]) -> dict[str, tuple[str, ...]]:
    modules = {_module_name_for_rel(item.file): item.file for item in facades}
    if not modules:
        return {}
    importers: dict[str, list[str]] = {item.file: [] for item in facades}
    for path in iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for module, facade_file in modules.items():
            if rel == facade_file:
                continue
            if f"import {module}" in text or f"from {module} import" in text:
                importers[facade_file].append(rel)
    return {facade: tuple(sorted(paths)) for facade, paths in importers.items()}


def _looks_like_facade(text: str) -> bool:
    meaningful = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not meaningful:
        return False
    import_export_lines = [line for line in meaningful if re.search(r"^\s*(from\s+\S+\s+import|import\s+\S+|__all__\s*=)", line)]
    has_wildcard = "import *" in text or "# noqa: F401" in text or "# noqa: F403" in text
    return has_wildcard and len(import_export_lines) >= max(2, len(meaningful) // 2)


def _looks_like_duplicate_rule_hotspot(rel: str, text: str) -> bool:
    if rel == "shared/text_cleanup_rules.py":
        return False
    regex_count = len(re.findall(r"re\.sub\(|re\.compile\(|\(r['\"]", text))
    replacement_count = text.count("replacement") + text.count("REPLACEMENTS")
    cleanup_words = sum(word in rel for word in ("cleanup", "polish", "quality", "parser", "generation"))
    return cleanup_words and (regex_count >= 10 or replacement_count >= 4)


def write_markdown(audit: OwnershipAudit, path: Path, *, fingerprint: ReportFingerprint | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Module Ownership Audit",
        "",
        "Generated by `scripts/module_ownership_audit.py`.",
        "",
        *_fingerprint_markdown(fingerprint),
        "## Overworked files",
        "",
    ]
    lines.extend(_table_files(audit.overworked_files[:40]))
    lines.extend(["", "## Long functions", ""])
    lines.extend(_table_functions(audit.long_functions[:60]))
    lines.extend(["", "## Facade-like modules", ""])
    lines.extend(_table_files(audit.facade_like_modules[:80]))
    lines.extend(["", "## Duplicate rule hotspots", ""])
    lines.extend(_table_files(audit.duplicate_rule_hotspots[:60]))
    lines.extend(["", "## Facade importers", ""])
    lines.extend(_table_facade_importers(audit.facade_importers))
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")



def _fingerprint_markdown(fingerprint: ReportFingerprint | None) -> list[str]:
    if fingerprint is None:
        return []
    clean = "yes" if fingerprint.working_tree_clean else "no"
    return [
        "## Repository fingerprint",
        "",
        f"- Repository HEAD: `{fingerprint.repository_head or 'unavailable'}`",
        f"- Committed tree: `{fingerprint.repository_head_tree or 'unavailable'}`",
        f"- Working tree clean: `{clean}`",
        f"- Audited Python source tree: `{fingerprint.python_source_tree_sha256}`",
        f"- Audited Python files: `{fingerprint.python_source_file_count}`",
        "",
    ]


def report_payload(audit: OwnershipAudit, fingerprint: ReportFingerprint) -> dict[str, object]:
    return {"report_fingerprint": fingerprint.to_dict(), **audit.to_dict()}

def _table_files(items: tuple[FileFinding, ...] | list[FileFinding]) -> list[str]:
    lines = ["| File | Lines | Concern |", "|---|---:|---|"]
    lines.extend(f"| `{item.file}` | {item.line_count} | {item.concern} |" for item in items)
    if len(lines) == 2:
        lines.append("| — | — | — |")
    return lines


def _table_facade_importers(importers: dict[str, tuple[str, ...]]) -> list[str]:
    lines = ["| Facade | Importers |", "|---|---:|"]
    for facade, paths in sorted(importers.items()):
        lines.append(f"| `{facade}` | {len(paths)} |")
    if len(lines) == 2:
        lines.append("| — | — |")
    return lines


def _table_functions(items: tuple[FunctionFinding, ...] | list[FunctionFinding]) -> list[str]:
    lines = ["| File | Function | Lines | Start |", "|---|---|---:|---:|"]
    lines.extend(f"| `{item.file}` | `{item.name}` | {item.line_count} | {item.start_line} |" for item in items)
    if len(lines) == 2:
        lines.append("| — | — | — | — |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=ROOT / "docs/reports/module_ownership_audit/latest.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "docs/reports/module_ownership_audit/latest.md")
    parser.add_argument("--file-line-limit", type=int, default=450)
    parser.add_argument("--function-line-limit", type=int, default=120)
    args = parser.parse_args()
    source_files = iter_python_files(ROOT)
    audit = run_audit(file_line_limit=args.file_line_limit, function_line_limit=args.function_line_limit)
    fingerprint = build_report_fingerprint(ROOT, source_files)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report_payload(audit, fingerprint), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(audit, args.markdown_output, fingerprint=fingerprint)
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")
    print(
        f"findings: files={len(audit.overworked_files)} functions={len(audit.long_functions)} "
        f"facades={len(audit.facade_like_modules)} duplicate_rule_hotspots={len(audit.duplicate_rule_hotspots)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
