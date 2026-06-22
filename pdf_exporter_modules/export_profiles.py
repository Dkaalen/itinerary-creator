"""PDF export profile definitions.

Profiles keep client/internal/compact export choices deterministic and testable
without duplicating exporter code.  The default remains the normal premium
client PDF.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PdfExportProfile:
    id: str
    label: str
    description: str
    filename_suffix: str
    margin_mm: int = 22
    top_margin_mm: int = 24
    bottom_margin_mm: int = 22
    min_compact_level: int = 0
    include_internal_notes: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PDF_EXPORT_PROFILES: tuple[PdfExportProfile, ...] = (
    PdfExportProfile(
        id="client_premium",
        label="Client PDF",
        description="Full premium client-ready itinerary.",
        filename_suffix="",
    ),
    PdfExportProfile(
        id="client_compact",
        label="Compact client PDF",
        description="Tighter layout for long itineraries while staying client-facing.",
        filename_suffix="compact",
        margin_mm=20,
        top_margin_mm=22,
        bottom_margin_mm=20,
        min_compact_level=1,
    ),
    PdfExportProfile(
        id="internal_review",
        label="Internal review PDF",
        description="Internal QA copy with a compact layout and review appendix.",
        filename_suffix="internal",
        margin_mm=20,
        top_margin_mm=22,
        bottom_margin_mm=20,
        min_compact_level=1,
        include_internal_notes=True,
    ),
)

_PROFILE_BY_ID = {profile.id: profile for profile in PDF_EXPORT_PROFILES}
DEFAULT_PDF_EXPORT_PROFILE = PDF_EXPORT_PROFILES[0]


def pdf_export_profile_options() -> tuple[dict[str, Any], ...]:
    return tuple(profile.as_dict() for profile in PDF_EXPORT_PROFILES)


def resolve_pdf_export_profile(value: str | Mapping[str, Any] | None) -> PdfExportProfile:
    if isinstance(value, Mapping):
        value = str(value.get("pdf_export_profile") or value.get("id") or "")
    profile_id = str(value or "").strip()
    return _PROFILE_BY_ID.get(profile_id, DEFAULT_PDF_EXPORT_PROFILE)


def pdf_filename(base_name: str = "itinerary_preview", profile: str | Mapping[str, Any] | None = None) -> str:
    resolved = resolve_pdf_export_profile(profile)
    suffix = f"_{resolved.filename_suffix}" if resolved.filename_suffix else ""
    return f"{base_name}{suffix}.pdf"
