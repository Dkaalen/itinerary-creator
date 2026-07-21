"""Audit compatibility facades and modules with no production importers.

This is a static, conservative report. It does not delete files; it gives cleanup
patches a repeatable map before retiring old wrappers.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    "app_modules",
    "calculator",
    "images",
    "itinerary_domain",
    "itinerary_generation",
    "normalizer_modules",
    "parser_modules",
    "pdf_exporter_modules",
    "project_storage",
    "shared",
    "text_polish_modules",
    "ui",
    "visual_editor_component",
)
SOURCE_EXCLUDED_PARTS = {"__pycache__", "tests"}
FACADE_MARKERS = (
    "backward-compatible",
    "compatibility facade",
    "legacy import path",
    "public import path",
    "wrapper",
)


@dataclass(frozen=True)
class ModuleAudit:
    module: str
    path: str
    is_facade: bool
    production_importers: tuple[str, ...]


def module_name_for_path(path: Path, root: Path = REPO_ROOT) -> str:
    """Return the importable module name for a Python source path."""

    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _source_files(root: Path = REPO_ROOT) -> tuple[Path, ...]:
    files = [path for path in root.glob("*.py") if path.is_file()]
    for source_root in SOURCE_ROOTS:
        base = root / source_root
        if not base.exists():
            continue
        files.extend(
            path
            for path in base.rglob("*.py")
            if not any(part in SOURCE_EXCLUDED_PARTS for part in path.relative_to(root).parts)
        )
    return tuple(sorted(set(files)))


def imported_modules_for_path(path: Path, root: Path = REPO_ROOT) -> set[str]:
    """Return absolute module references, including relative/submodule imports."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()

    module_name = module_name_for_path(path, root)
    package_name = module_name if path.name == "__init__.py" else module_name.rpartition(".")[0]
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level:
            package_parts = package_name.split(".") if package_name else []
            parent_levels = node.level - 1
            if parent_levels > len(package_parts):
                base_parts: list[str] = []
            elif parent_levels:
                base_parts = package_parts[:-parent_levels]
            else:
                base_parts = package_parts
            if node.module:
                base_parts = [*base_parts, *node.module.split(".")]
        else:
            base_parts = node.module.split(".") if node.module else []

        base_module = ".".join(base_parts)
        if base_module:
            modules.add(base_module)
        for alias in node.names:
            if alias.name == "*":
                continue
            imported_submodule = ".".join([*base_parts, alias.name])
            if imported_submodule:
                modules.add(imported_submodule)

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


def audit_modules(root: Path = REPO_ROOT) -> tuple[ModuleAudit, ...]:
    files = _source_files(root)
    module_by_path = {path: module_name_for_path(path, root) for path in files}
    importers: dict[str, set[str]] = {module: set() for module in module_by_path.values()}
    for importer_path in files:
        importer = module_by_path[importer_path]
        for imported in imported_modules_for_path(importer_path, root):
            for module in importers:
                if imported == module or imported.startswith(module + "."):
                    if importer != module:
                        importers[module].add(importer)
    return tuple(
        ModuleAudit(
            module=module,
            path=str(path.relative_to(root)),
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
