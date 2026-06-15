from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from images import image_bank
from scripts.artifact_hygiene import is_artifact_noise_path, iter_clean_artifact_files
from scripts.test_groups import empty_legacy_test_modules

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_image_bank_bootstrap_is_opt_in_by_default(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    placeholder = root / "itinerary-image-bank"
    fallback = root / "image_bank"
    placeholder.mkdir(parents=True)
    fallback.mkdir(parents=True)
    (root / ".gitmodules").write_text('[submodule "itinerary-image-bank"]\n', encoding="utf-8")

    monkeypatch.delenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", raising=False)

    def fail_if_called(*args, **kwargs):  # pragma: no cover - only runs on regression
        raise AssertionError("runtime git clone/pull should be opt-in")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    assert image_bank.get_image_bank_paths(root) == [fallback]


def test_runtime_image_bank_bootstrap_allows_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    assert image_bank._runtime_bootstrap_allowed() is True


def test_gitignore_blocks_patch_artifact_noise():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for pattern in (
        ".cache/",
        ".pytest_cache/",
        ".runtime_image_bank/",
        "__pycache__/",
        "*.py[cod]",
        "*.zip",
        "outputs/",
        "persistent_drafts/",
        "qa_reports/",
    ):
        assert pattern in gitignore


def test_artifact_hygiene_filters_generated_noise(tmp_path):
    keep = tmp_path / "itinerary_generation" / "transport.py"
    keep.parent.mkdir(parents=True)
    keep.write_text("# source\n", encoding="utf-8")

    noise_files = [
        tmp_path / ".cache" / "puppeteer" / "chrome",
        tmp_path / ".git" / "index",
        tmp_path / ".pytest_cache" / "README.md",
        tmp_path / "module" / "__pycache__" / "x.pyc",
        tmp_path / ".runtime_image_bank" / "repo" / "image.webp",
        tmp_path / "persistent_drafts" / "draft.json",
        tmp_path / "qa_reports" / "report.json",
        tmp_path / "scratch.tmp",
        tmp_path / "patch.zip",
        tmp_path / ".chatgpt_write_test.txt",
    ]
    for path in noise_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("noise", encoding="utf-8")

    assert is_artifact_noise_path(".cache/puppeteer/chrome")
    assert is_artifact_noise_path(".git/index")
    assert is_artifact_noise_path("module/__pycache__/x.pyc")
    assert is_artifact_noise_path(".runtime_image_bank/repo/image.webp")
    assert is_artifact_noise_path("persistent_drafts/draft.json")
    assert is_artifact_noise_path("qa_reports/report.json")
    assert is_artifact_noise_path("scratch.tmp")
    assert not is_artifact_noise_path("itinerary_generation/transport.py")

    assert list(iter_clean_artifact_files(tmp_path)) == [keep]


def test_clean_zip_builder_excludes_local_artifacts(tmp_path):
    from scripts.build_clean_zip import build_clean_zip

    root = tmp_path / "itinerary-creator-git"
    source = root / "app_modules" / "main_view.py"
    source.parent.mkdir(parents=True)
    source.write_text("# source\n", encoding="utf-8")

    noise_files = [
        root / ".cache" / "puppeteer" / "chrome",
        root / ".git" / "index",
        root / ".pytest_cache" / "README.md",
        root / "app_modules" / "__pycache__" / "main_view.cpython-312.pyc",
        root / "outputs" / "itinerary.pdf",
        root / "persistent_drafts" / "draft.json",
        root / "qa_reports" / "report.json",
        root / "backup.bak",
        root / "old_patch.zip",
    ]
    for path in noise_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("noise", encoding="utf-8")

    output, file_count = build_clean_zip(root, tmp_path / "clean.zip")

    assert file_count == 1
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["app_modules/main_view.py"]


def test_bundled_default_images_are_right_sized_for_pdf_and_screen_use():
    from PIL import Image

    default_dir = ROOT / "image_bank" / "Default"
    assert default_dir.exists()

    oversized = []
    for path in sorted(default_dir.glob("*.webp")):
        with Image.open(path) as image:
            width, height = image.size
        if max(width, height) > 2400 or path.stat().st_size > 1_250_000:
            oversized.append(f"{path.name}: {width}x{height}, {path.stat().st_size} bytes")

    assert oversized == []


def test_empty_legacy_test_modules_have_been_removed_from_source_tree():
    assert empty_legacy_test_modules() == frozenset()
    removed_modules = {
        "test_images.py",
        "test_regressions.py",
        "test_regressions_content_generation.py",
        "test_regressions_rendering.py",
    }
    for module_name in removed_modules:
        assert not (ROOT / "tests" / module_name).exists()


def test_first_party_code_no_longer_imports_transport_compatibility_facades():
    facade_modules = {
        "itinerary_generation.transport_routes",
        "itinerary_generation.transport_titles",
        "itinerary_generation.inclusion_transport",
        "parser_modules.transport_titles",
    }
    allowed_files = {
        Path("itinerary_generation/transport_routes.py"),
        Path("itinerary_generation/transport_titles.py"),
        Path("itinerary_generation/inclusion_transport.py"),
        Path("parser_modules/transport_titles.py"),
        Path("tests/test_patch_ai_transport_domain.py"),
        Path("tests/test_patch_ak_cleanup_hygiene.py"),
        Path("tests/test_finland_transport_regressions.py"),
        Path("tests/test_fixture_quality_polish.py"),
        Path("tests/test_patch_n_editor_image_safety.py"),
        Path("tests/test_stress_logic_followups.py"),
        Path("tests/test_transport_model_architecture.py"),
    }

    offenders = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if relative in allowed_files:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for module in facade_modules:
            if f"from {module} import" in text or f"import {module}" in text:
                offenders.append(f"{relative}: {module}")

    assert offenders == []
