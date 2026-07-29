from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_real_streamlit_secrets_are_local_only() -> None:
    assert not (ROOT / ".streamlit" / "secrets.toml").exists()
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".streamlit/secrets.toml" in ignored


def test_streamlit_secrets_example_contains_schema_without_key_material() -> None:
    example = (ROOT / ".streamlit" / "secrets.example.toml").read_text(encoding="utf-8")

    assert "[local_library]" in example
    assert "[gcp_service_account]" in example
    assert "SUPABASE_SECRET_KEY" in example
    assert "replace-with-private-key-from-secure-secret-store" in example
    assert "-----BEGIN PRIVATE KEY-----" not in example
    assert "-----BEGIN RSA PRIVATE KEY-----" not in example
    assert "-----BEGIN EC PRIVATE KEY-----" not in example


def test_readme_requires_protected_secret_storage_and_rotation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert ".streamlit/secrets.example.toml" in readme
    assert ".streamlit/secrets.toml" in readme
    assert "must never be committed" in readme
    assert "rotate or revoke" in readme
