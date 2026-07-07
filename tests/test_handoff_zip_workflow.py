from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path
from tests.support.static_contracts import read_contract_text

from scripts.artifact_hygiene import is_artifact_noise_path, sensitive_artifact_text_hits
from scripts.build_handoff_zip import build_handoff_zip, default_handoff_output_path
from scripts.validate_handoff_zip import validate_handoff_zip

ROOT = Path(__file__).resolve().parents[1]


def test_handoff_zip_uses_safe_default_name(tmp_path) -> None:
    project = tmp_path / "itinerary-creator-git"
    project.mkdir()

    assert default_handoff_output_path(project) == tmp_path / "itinerary-creator-git-handoff.zip"


def test_handoff_zip_excludes_artifacts_and_keeps_safe_examples(tmp_path) -> None:
    project = tmp_path / "itinerary-creator-git"
    source = project / "app_modules" / "main_view.py"
    secret = project / ".streamlit" / "secrets.toml"
    secret_example = project / ".streamlit" / "secrets.example.toml"
    git_object = project / ".git" / "objects" / "pack" / "pack.bin"
    cache_file = project / "tests" / "__pycache__" / "test.cpython-311.pyc"
    old_zip = project / "old-handoff.zip"
    output = tmp_path / "custom-handoff.zip"

    for path, content in (
        (source, "# source\n"),
        (secret, "private_key = 'secret'\n"),
        (secret_example, "[local_library]\nspreadsheet_id = 'example'\n"),
        (git_object, "git data"),
        (cache_file, "bytecode"),
        (old_zip, "zip data"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    zip_path, file_count = build_handoff_zip(project, output)

    assert zip_path == output
    assert file_count == 2
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.namelist()
        assert members == [".streamlit/secrets.example.toml", "app_modules/main_view.py"]
        assert all(not is_artifact_noise_path(member) for member in members)
        combined = "\n".join(archive.read(member).decode("utf-8") for member in members)
        assert "private_key = 'secret'" not in combined


def test_handoff_zip_cli_builds_package(tmp_path) -> None:
    project = tmp_path / "itinerary-creator-git"
    source = project / "README.md"
    source.parent.mkdir(parents=True)
    source.write_text("# test project\n", encoding="utf-8")
    output = tmp_path / "handoff.zip"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_handoff_zip.py"),
            "--root",
            str(project),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Created handoff ZIP" in result.stdout
    assert output.exists()
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["README.md"]


def test_readme_documents_standard_handoff_zip_and_deletion_workflow() -> None:
    readme = read_contract_text("README.md")

    assert "python scripts/build_handoff_zip.py" in readme
    assert "do not manually compress the whole working tree" in readme
    assert "python scripts/validate_handoff_zip.py" in readme
    assert "git rm" in readme


def test_architecture_progress_uses_current_patch_delivery_standard() -> None:
    progress = read_contract_text("ARCHITECTURE_CLEANUP_PROGRESS.md")
    workflow = progress.split("## Architecture principle", maxsplit=1)[0]

    assert "Use **patch** for each implementation unit" in workflow
    assert "git add -- $files" in workflow
    assert "git rm --ignore-unmatch" in workflow
    assert "git add ." in workflow
    assert "Patch one batch at a time" not in workflow
    assert "After a final batch patch" not in workflow


def test_handoff_zip_validator_rejects_manual_zip_with_secrets_and_git_metadata(tmp_path) -> None:
    manual_zip = tmp_path / "manual-full-working-tree.zip"
    with zipfile.ZipFile(manual_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(".git/index", "git metadata")
        archive.writestr("app_modules/__pycache__/main.cpython-312.pyc", "bytecode")
        archive.writestr(".streamlit/secrets.toml", "private_key = '-----BEGIN PRIVATE KEY----- secret'")
        archive.writestr("app_modules/main_view.py", "# source\n")

    issues = validate_handoff_zip(manual_zip)

    rendered = "\n".join(f"{issue.member}: {issue.reason}" for issue in issues)
    assert ".git/index" in rendered
    assert "__pycache__" in rendered
    assert ".streamlit/secrets.toml" in rendered


def test_handoff_zip_validator_passes_official_clean_zip(tmp_path) -> None:
    project = tmp_path / "itinerary-creator-git"
    source = project / "app_modules" / "main_view.py"
    source.parent.mkdir(parents=True)
    source.write_text("# source\n", encoding="utf-8")
    (project / ".streamlit").mkdir()
    (project / ".streamlit" / "secrets.example.toml").write_text("[local_library]\n", encoding="utf-8")
    output = tmp_path / "handoff.zip"

    zip_path, _file_count = build_handoff_zip(project, output)

    assert validate_handoff_zip(zip_path) == ()


def test_sensitive_artifact_text_guard_detects_private_key_material() -> None:
    assert sensitive_artifact_text_hits("token -----BEGIN PRIVATE KEY----- token") == ("-----BEGIN PRIVATE KEY-----",)
