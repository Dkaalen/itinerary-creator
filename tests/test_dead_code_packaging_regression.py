from __future__ import annotations

import ast
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.artifact_hygiene import is_artifact_noise_path
from scripts.build_clean_zip import build_clean_zip
from scripts.import_smoke import discover_production_modules, run_import_smoke

ROOT = Path(__file__).resolve().parents[1]

REMOVED_PATHS = (
    Path("ui/transport_blocks.py"),
    Path("visual_editor_component/app_modules/main_view.py"),
    Path("visual_editor_component/app_modules/export_step.py"),
    Path("visual_editor_component/app_modules/workflow_shell.py"),
    Path("visual_editor_component/ui/styles.py"),
    Path("_PATCH_DELETE_FILES.txt"),
)

REMOVED_MODULES = frozenset(
    {
        "ui.transport_blocks",
        "visual_editor_component.app_modules.main_view",
        "visual_editor_component.app_modules.export_step",
        "visual_editor_component.app_modules.workflow_shell",
        "visual_editor_component.ui.styles",
    }
)

PRODUCTION_SOURCE_ROOTS = (
    "app_modules",
    "images",
    "itinerary_generation",
    "normalizer_modules",
    "parser_modules",
    "pdf_exporter_modules",
    "shared",
    "text_polish_modules",
    "ui",
    "visual_editor_component",
)


def _production_python_files(root: Path = ROOT):
    for source_root in PRODUCTION_SOURCE_ROOTS:
        base = root / source_root
        for path in base.rglob("*.py"):
            relative = path.relative_to(root)
            if any(part in {"__pycache__", "tests", "frontend"} for part in relative.parts):
                continue
            yield path


def test_obsolete_compatibility_files_stay_deleted() -> None:
    for relative in REMOVED_PATHS:
        assert not (ROOT / relative).exists(), f"obsolete file returned: {relative}"


def test_no_static_or_dynamic_production_references_remain() -> None:
    offenders: list[str] = []
    for path in _production_python_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(ROOT)
        for removed_module in REMOVED_MODULES:
            if removed_module in source:
                offenders.append(f"{relative}: string reference to {removed_module}")

        tree = ast.parse(source, filename=str(relative))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported = {node.module or ""}
            else:
                continue
            for imported_module in imported:
                if imported_module in REMOVED_MODULES:
                    offenders.append(f"{relative}: imports {imported_module}")

    assert offenders == []


def test_artifact_policy_rejects_browser_cache_and_runtime_outputs() -> None:
    forbidden = (
        ".cache/puppeteer/chrome",
        ".git/objects/pack/data",
        "module/__pycache__/module.pyc",
        "outputs/itinerary_preview.pdf",
        "persistent_drafts/draft.json",
        "qa_reports/quality.json",
        "temporary.tmp",
        "backup.bak",
        "handoff.zip",
    )
    assert all(is_artifact_noise_path(path) for path in forbidden)


def test_production_import_smoke_has_no_non_optional_failures(monkeypatch) -> None:
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")
    modules = discover_production_modules()
    skipped, failures = run_import_smoke(modules)

    assert len(modules) >= 250
    assert failures == ()
    assert all(module for module in skipped)


def test_clean_zip_survives_fresh_extraction(tmp_path) -> None:
    archive_path, file_count = build_clean_zip(ROOT, tmp_path / "itinerary-creator-git-clean.zip")
    assert file_count > 300

    with zipfile.ZipFile(archive_path) as archive:
        members = archive.namelist()
        assert members == sorted(members)
        assert all(not is_artifact_noise_path(member) for member in members)
        assert all(relative.as_posix() not in members for relative in REMOVED_PATHS)
        archive.extractall(tmp_path / "extracted")

    extracted = tmp_path / "extracted"
    environment = os.environ.copy()
    environment["ITINERARY_IMAGE_BANK_BOOTSTRAP"] = "0"

    compile_result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "."],
        cwd=extracted,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    import_result = subprocess.run(
        [sys.executable, "scripts/import_smoke.py"],
        cwd=extracted,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert import_result.returncode == 0, import_result.stdout + import_result.stderr
