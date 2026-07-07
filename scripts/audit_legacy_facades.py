"""Audit compatibility facades and modules with no production importers.

This is a static, conservative report. It does not delete files; it gives cleanup
patches a repeatable map before retiring old wrappers.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("app_modules", "calculator", "images", "itinerary_generation", "normalizer_modules", "parser_modules", "pdf_exporter_modules", "project_storage", "text_polish_modules", "ui", "visual_editor_component")
FACADE_MARKERS = ("compatibility facade", "legacy import path", "public import path", "wrapper")


@dataclass(frozen=True)
class ModuleAudit:
    module: str
    path: str
    is_facade: bool
    production_importers: tuple[str, ...]


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(REPO_ROOT).with_suffix("").parts)


def _source_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        base = REPO_ROOT / root
        if base.exists():
            files.extend(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)
    return tuple(sorted(files))


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


def _looks_like_facade(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if any(marker in text[:600] for marker in FACADE_MARKERS):
        return True
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    function_count = sum(isinstance(node, ast.FunctionDef) for node in tree.body)
    import_count = sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    return function_count <= 2 and import_count >= 1 and "__all__" in text


def audit_modules() -> tuple[ModuleAudit, ...]:
    files = _source_files()
    module_by_path = {path: _module_name(path) for path in files}
    importers: dict[str, set[str]] = {module: set() for module in module_by_path.values()}
    for importer_path in files:
        importer = module_by_path[importer_path]
        for imported in _imports(importer_path):
            for module in importers:
                if imported == module or imported.startswith(module + "."):
                    if importer != module:
                        importers[module].add(importer)
    return tuple(
        ModuleAudit(
            module=module,
            path=str(path.relative_to(REPO_ROOT)),
            is_facade=_looks_like_facade(path),
            production_importers=tuple(sorted(importers[module])),
        )
        for path, module in sorted(module_by_path.items(), key=lambda item: item[1])
    )


def render_markdown(audit: tuple[ModuleAudit, ...]) -> str:
    facades = [item for item in audit if item.is_facade]
    unimported = [item for item in audit if not item.production_importers]
    lines = [
        "# Legacy facade audit",
        "",
        "Static report generated from production modules only. Tests and dynamic imports are intentionally excluded, so candidates need human review before deletion.",
        "",
        f"Production modules scanned: {len(audit)}",
        f"Facade-like modules: {len(facades)}",
        f"Modules with no production importers: {len(unimported)}",
        "",
        "## Facade-like modules",
        "",
    ]
    for item in facades:
        lines.append(f"- `{item.path}` — importers: {len(item.production_importers)}")
    lines.extend(["", "## No production importers", ""])
    for item in unimported:
        lines.append(f"- `{item.path}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print(render_markdown(audit_modules()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
