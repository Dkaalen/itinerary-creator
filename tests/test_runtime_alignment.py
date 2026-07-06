from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_files_target_python_314() -> None:
    assert (ROOT / "runtime.txt").read_text(encoding="utf-8").strip() == "python-3.14"
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14"


def test_ci_uses_same_python_runtime_as_streamlit_cloud() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "python-version: '3.14'" in workflow
    assert "python-version: '3.11'" not in workflow
