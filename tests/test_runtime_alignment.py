from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_files_target_python_314() -> None:
    assert read_contract_text("runtime.txt").strip() == "python-3.13"
    assert read_contract_text(".python-version").strip() == "3.13"


def test_ci_uses_same_python_runtime_as_streamlit_cloud() -> None:
    workflow = read_contract_text(ROOT / ".github" / "workflows" / "tests.yml")

    assert "python-version: '3.13'" in workflow
    assert "python-version: '3.11'" not in workflow
