"""Build the tiny frontend signal used for hard editor commits."""

from __future__ import annotations


def build_editor_commit_signal_payload(source_signature: str | None = "") -> dict:
    """Return a minimal payload that tells the mounted editor to commit itself.

    The browser already owns the visible editor model at this point. Re-sending
    the full image-heavy editor payload just to trigger a PDF/Add Pictures sync
    makes the transition slow, so the commit rerun sends only this signal.
    """

    return {
        "meta": {
            "draft_schema_version": 3,
            "source_signature": str(source_signature or ""),
        },
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {},
        "workflow": {"commit_signal_only": True},
        "document_pages": [],
        "issue_flags": [],
    }
