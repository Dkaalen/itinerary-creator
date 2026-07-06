"""Pure PDF artifact authority for preview/export state.

PDF bytes are only reusable when they match the current export signature.  The
preview signature alone is not enough because a user can change image choices,
removed-image state, crop focus, cover imagery, or other export-only settings
without changing the generated HTML preview signature.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.export_identity import export_signature_for_state

PDF_BYTES_KEY = "pdf_bytes"
PDF_SIGNATURE_KEY = "pdf_signature"
EXPORT_PDF_BYTES_KEY = "export_pdf_bytes"
EXPORT_PDF_SIGNATURE_KEY = "export_pdf_signature"
PDF_FILENAME_KEY = "pdf_filename"
PDF_STATUS_KEY = "pdf_status"
DEFAULT_PDF_FILENAME = "itinerary_preview.pdf"

PDF_ARTIFACT_KEYS = (
    PDF_BYTES_KEY,
    EXPORT_PDF_BYTES_KEY,
    PDF_SIGNATURE_KEY,
    EXPORT_PDF_SIGNATURE_KEY,
)
PDF_ARTIFACT_TRANSIENT_KEYS = (
    PDF_FILENAME_KEY,
    "export_last_error",
    "_pdf_image_contract_cache",
)


@dataclass(frozen=True)
class CurrentPdfArtifact:
    """A current PDF artifact resolved from session-like state."""

    content: bytes
    signature: str
    filename: str = DEFAULT_PDF_FILENAME


def _bytes_or_none(value: Any) -> bytes | None:
    return value if isinstance(value, bytes | bytearray) and len(value) > 0 else None


def current_pdf_artifact(state: Mapping[str, Any]) -> CurrentPdfArtifact | None:
    """Return reusable PDF bytes only when the export signature is current."""

    current_signature = export_signature_for_state(state)
    if not current_signature:
        return None

    export_bytes = _bytes_or_none(state.get(EXPORT_PDF_BYTES_KEY))
    if export_bytes and state.get(EXPORT_PDF_SIGNATURE_KEY) == current_signature:
        return CurrentPdfArtifact(
            content=bytes(export_bytes),
            signature=current_signature,
            filename=str(state.get(PDF_FILENAME_KEY) or DEFAULT_PDF_FILENAME),
        )

    pdf_bytes = _bytes_or_none(state.get(PDF_BYTES_KEY))
    if pdf_bytes and state.get(PDF_SIGNATURE_KEY) == current_signature:
        return CurrentPdfArtifact(
            content=bytes(pdf_bytes),
            signature=current_signature,
            filename=str(state.get(PDF_FILENAME_KEY) or DEFAULT_PDF_FILENAME),
        )

    return None


def pdf_artifact_is_current(state: Mapping[str, Any]) -> bool:
    """Return whether state contains bytes for the current export signature."""

    return current_pdf_artifact(state) is not None


def store_pdf_artifact(
    state: MutableMapping[str, Any],
    *,
    content: bytes,
    signature: str | None,
    filename: str = DEFAULT_PDF_FILENAME,
) -> None:
    """Store a PDF artifact using the export signature as the authority."""

    if not signature:
        raise ValueError("PDF artifact cannot be stored without an export signature.")
    pdf_bytes = bytes(content)
    state[PDF_BYTES_KEY] = pdf_bytes
    state[EXPORT_PDF_BYTES_KEY] = pdf_bytes
    state[PDF_SIGNATURE_KEY] = signature
    state[EXPORT_PDF_SIGNATURE_KEY] = signature
    state[PDF_FILENAME_KEY] = filename or DEFAULT_PDF_FILENAME
    state[PDF_STATUS_KEY] = "Ready"
    state["export_last_error"] = ""


def mirror_current_pdf_artifact(state: MutableMapping[str, Any], artifact: CurrentPdfArtifact) -> None:
    """Normalize legacy/partial artifact keys after a current artifact is found."""

    state[PDF_BYTES_KEY] = artifact.content
    state[EXPORT_PDF_BYTES_KEY] = artifact.content
    state[PDF_SIGNATURE_KEY] = artifact.signature
    state[EXPORT_PDF_SIGNATURE_KEY] = artifact.signature
    state[PDF_FILENAME_KEY] = artifact.filename or DEFAULT_PDF_FILENAME
    state[PDF_STATUS_KEY] = "Ready"


def clear_pdf_artifact_state(state: MutableMapping[str, Any], *, status: str = "Not created") -> None:
    """Drop PDF bytes, signatures, and stale export-only caches."""

    for key in PDF_ARTIFACT_KEYS:
        state[key] = None
    for key in PDF_ARTIFACT_TRANSIENT_KEYS:
        state.pop(key, None)
    state[PDF_STATUS_KEY] = status


__all__ = [
    "CurrentPdfArtifact",
    "DEFAULT_PDF_FILENAME",
    "PDF_ARTIFACT_KEYS",
    "PDF_ARTIFACT_TRANSIENT_KEYS",
    "clear_pdf_artifact_state",
    "current_pdf_artifact",
    "mirror_current_pdf_artifact",
    "pdf_artifact_is_current",
    "store_pdf_artifact",
]
