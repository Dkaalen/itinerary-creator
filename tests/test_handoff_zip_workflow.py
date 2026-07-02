from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.artifact_hygiene import is_artifact_noise_path
from scripts.build_handoff_zip import build_handoff_zip, default_handoff_output_path

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
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "python scripts/build_handoff_zip.py" in readme
    assert "do not manually compress the whole working tree" in readme
    assert "git rm" in readme
