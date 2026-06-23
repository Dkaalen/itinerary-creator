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
    audience: str = "Client"
    use_case: str = "Client-ready itinerary proposal"
    document_label: str = "TRAVEL ITINERARY"
    client_ready: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def selector_label(self) -> str:
        return f"{self.label} · {self.audience}"


PDF_EXPORT_PROFILES: tuple[PdfExportProfile, ...] = (
    PdfExportProfile(
        id="client_premium",
        label="Luxury Proposal",
        description="Full premium client-ready proposal with the most polished spacing and editorial rhythm.",
        filename_suffix="",
        audience="Client",
        use_case="Best for high-value proposals and polished final itinerary delivery.",
        document_label="LUXURY PROPOSAL",
    ),
    PdfExportProfile(
        id="client_compact",
        label="Compact Itinerary",
        description="Tighter client-facing layout for long itineraries while keeping the proposal clean.",
        filename_suffix="compact",
        margin_mm=20,
        top_margin_mm=22,
        bottom_margin_mm=20,
        min_compact_level=1,
        audience="Client",
        use_case="Best when the itinerary is long and page count matters.",
        document_label="TRAVEL ITINERARY",
    ),
    PdfExportProfile(
        id="client_detailed",
        label="Detailed Travel Plan",
        description="Client-facing detailed version for review calls and operationally rich proposals.",
        filename_suffix="detailed",
        audience="Client / Advisor",
        use_case="Best for walkthroughs where the client or advisor needs more context.",
        document_label="DETAILED TRAVEL PLAN",
    ),
    PdfExportProfile(
        id="internal_review",
        label="Internal Ops Version",
        description="Internal QA copy with compact layout and review appendix. Not intended for clients.",
        filename_suffix="internal",
        margin_mm=20,
        top_margin_mm=22,
        bottom_margin_mm=20,
        min_compact_level=1,
        include_internal_notes=True,
        audience="Internal",
        use_case="Best for agency/DMC checks before client delivery.",
        document_label="INTERNAL REVIEW",
        client_ready=False,
    ),
)
_PROFILE_BY_ID = {profile.id: profile for profile in PDF_EXPORT_PROFILES}
DEFAULT_PDF_EXPORT_PROFILE = PDF_EXPORT_PROFILES[0]


def pdf_export_profile_options() -> tuple[dict[str, Any], ...]:
    options = []
    for profile in PDF_EXPORT_PROFILES:
        data = profile.as_dict()
        data["selector_label"] = profile.selector_label
        options.append(data)
    return tuple(options)


def resolve_pdf_export_profile(value: str | Mapping[str, Any] | None) -> PdfExportProfile:
    if isinstance(value, Mapping):
        value = str(value.get("pdf_export_profile") or value.get("id") or "")
    profile_id = str(value or "").strip()
    return _PROFILE_BY_ID.get(profile_id, DEFAULT_PDF_EXPORT_PROFILE)


def pdf_filename(base_name: str = "itinerary_preview", profile: str | Mapping[str, Any] | None = None) -> str:
    resolved = resolve_pdf_export_profile(profile)
    suffix = f"_{resolved.filename_suffix}" if resolved.filename_suffix else ""
    return f"{base_name}{suffix}.pdf"
