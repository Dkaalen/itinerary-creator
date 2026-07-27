"""Supported public API for PDF export in Itinerary Creator.

Importing this module is deliberately lightweight.  ReportLab, BeautifulSoup,
Pillow, and all rendering implementation modules are imported only when an
export function is called.  Application code should use :func:`create_pdf` and
inspect the returned :class:`PdfExportResult` instead of importing implementation
modules from :mod:`pdf_exporter_modules`.

A small set of legacy helper attributes remains available lazily for older tests
and scripts.  Those compatibility attributes are not part of ``__all__`` and are
not the supported application boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module as _import_module
from pathlib import Path
from typing import Any, Mapping

from pdf_exporter_modules.export_profiles import (
    PdfExportProfile,
    pdf_export_profile_options,
    pdf_filename,
    resolve_pdf_export_profile,
)


PDF_DEPENDENCY_ROOTS = frozenset({"PIL", "bs4", "reportlab"})


@dataclass(frozen=True, slots=True)
class PdfExportResult:
    """Supported result for one PDF creation attempt."""

    status: str
    path: Path | None = None
    renderer: str = ""
    error_code: str = ""
    message: str = ""
    dependency: str = ""
    technical_detail: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "created" and self.path is not None

    @property
    def failed(self) -> bool:
        return not self.succeeded


def _failure(
    *,
    status: str,
    error_code: str,
    message: str,
    dependency: str = "",
    technical_detail: str = "",
    renderer: str = "",
) -> PdfExportResult:
    return PdfExportResult(
        status=status,
        error_code=error_code,
        message=message,
        dependency=dependency,
        technical_detail=technical_detail,
        renderer=renderer,
    )


def _dependency_name(error: BaseException) -> str:
    name = str(getattr(error, "name", "") or "").strip()
    return name.split(".", 1)[0] if name else ""


def _dependency_failure(error: BaseException, *, renderer: str) -> PdfExportResult | None:
    dependency = _dependency_name(error)
    if dependency not in PDF_DEPENDENCY_ROOTS:
        return None
    return _failure(
        status="dependency_unavailable",
        error_code="pdf_dependency_unavailable",
        message=(
            "PDF creation is unavailable because a required PDF dependency "
            f"({dependency}) could not be loaded. The itinerary preview was not changed."
        ),
        dependency=dependency,
        technical_detail=f"{type(error).__name__}: {error}",
        renderer=renderer,
    )


def create_pdf(
    html_path: str | Path,
    pdf_path: str | Path,
    *,
    render_document: Any = None,
    color_data: Mapping[str, Any] | None = None,
    day_images: Mapping[str, Mapping[str, Any] | None] | None = None,
    day_image_crop_focus: Mapping[str, str] | None = None,
    output_edits: Mapping[str, Any] | None = None,
    export_profile: str | Mapping[str, Any] | None = None,
    output_brand: str = "agent",
) -> PdfExportResult:
    """Create one PDF and return a stable success/failure result.

    The function performs no heavy imports until it has validated the request.
    Typed ``RenderDocument`` export remains preferred; unsupported saved HTML
    continues to use the established HTML fallback renderer.
    """

    source_path = Path(html_path).resolve() if html_path else None
    destination_path = Path(pdf_path).resolve() if pdf_path else None
    if source_path is None or not source_path.exists():
        return _failure(
            status="invalid_request",
            error_code="pdf_html_preview_missing",
            message="PDF creation requires the current HTML preview file.",
        )
    if destination_path is None:
        return _failure(
            status="invalid_request",
            error_code="pdf_destination_missing",
            message="PDF creation requires an output path.",
        )

    edits = output_edits or {}
    renderer = "html"
    try:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if render_document is not None:
            fallback_module = _import_module("pdf_exporter_modules.pdf_html_fallback")
            requires_fallback = fallback_module.render_document_requires_html_fallback(
                render_document,
                edits,
            )
            if not requires_fallback:
                renderer = "typed"
                typed_module = _import_module("pdf_exporter_modules.typed_exporter")
                typed_module.export_render_document_to_pdf(
                    render_document,
                    destination_path,
                    color_data=color_data,
                    day_images=day_images,
                    day_image_crop_focus=day_image_crop_focus,
                    export_profile=export_profile,
                    output_brand=output_brand,
                )
            else:
                html_module = _import_module("pdf_exporter_modules.exporter")
                html_module.export_html_to_pdf(source_path, destination_path)
        else:
            html_module = _import_module("pdf_exporter_modules.exporter")
            html_module.export_html_to_pdf(source_path, destination_path)
    except (ImportError, ModuleNotFoundError) as error:
        dependency_result = _dependency_failure(error, renderer=renderer)
        if dependency_result is not None:
            return dependency_result
        return _failure(
            status="failed",
            error_code="pdf_export_import_failed",
            message="PDF creation could not load its renderer. The itinerary preview was not changed.",
            technical_detail=f"{type(error).__name__}: {error}",
            renderer=renderer,
        )
    except Exception as error:  # UI boundary converts renderer failures into a stable result.
        return _failure(
            status="failed",
            error_code="pdf_export_failed",
            message="PDF creation failed. The itinerary preview was not changed.",
            technical_detail=f"{type(error).__name__}: {error}",
            renderer=renderer,
        )

    if not destination_path.exists() or destination_path.stat().st_size <= 0:
        return _failure(
            status="failed",
            error_code="pdf_output_missing",
            message="PDF creation completed without producing a usable file.",
            renderer=renderer,
        )
    return PdfExportResult(status="created", path=destination_path, renderer=renderer)


# Legacy call-level compatibility.  These wrappers remain lazy and intentionally
# sit outside the supported ``__all__`` surface.
def export_html_to_pdf(html_path: str | Path, pdf_path: str | Path):
    implementation = _import_module("pdf_exporter_modules.exporter")
    return implementation.export_html_to_pdf(html_path, pdf_path)


def export_render_document_to_pdf(render_document: Any, pdf_path: str | Path, **kwargs: Any):
    implementation = _import_module("pdf_exporter_modules.typed_exporter")
    return implementation.export_render_document_to_pdf(render_document, pdf_path, **kwargs)


def render_document_requires_html_fallback(render_document: Any, output_edits: Mapping[str, Any] | None = None) -> bool:
    implementation = _import_module("pdf_exporter_modules.pdf_html_fallback")
    return bool(implementation.render_document_requires_html_fallback(render_document, output_edits))


_LEGACY_SYMBOL_EXPORTS: dict[str, tuple[str, str]] = {
    "BODY": ("styles", "BODY"),
    "CARD": ("styles", "CARD"),
    "DEFAULT_PDF_COLORS": ("styles", "DEFAULT_PDF_COLORS"),
    "INK": ("styles", "INK"),
    "LINE": ("styles", "LINE"),
    "MUTED": ("styles", "MUTED"),
    "PAGE_BACKGROUND": ("styles", "PAGE_BACKGROUND"),
    "PDF_CROP_FOCUS_FACTORS": ("image_constants", "PDF_CROP_FOCUS_FACTORS"),
    "PDF_CROP_VERTICAL_FOCUS": ("image_constants", "PDF_CROP_VERTICAL_FOCUS"),
    "PDF_IMAGE_BOTTOM_Y": ("image_constants", "PDF_IMAGE_BOTTOM_Y"),
    "PDF_IMAGE_GAP": ("image_constants", "PDF_IMAGE_GAP"),
    "PDF_IMAGE_HALF_OFFSET": ("image_constants", "PDF_IMAGE_HALF_OFFSET"),
    "PDF_MIN_IMAGE_HEIGHT": ("image_constants", "PDF_MIN_IMAGE_HEIGHT"),
    "SamePageDayImage": ("same_page_image_flowable", "SamePageDayImage"),
    "_activity_time_range_text": ("render_content", "_activity_time_range_text"),
    "add_bullets": ("story", "add_bullets"),
    "add_day_image_if_possible": ("day_images", "add_day_image_if_possible"),
    "add_paragraph": ("story", "add_paragraph"),
    "apply_pdf_palette": ("styles", "apply_pdf_palette"),
    "calculate_day_image_layout": ("image_layout", "calculate_day_image_layout"),
    "clean_text": ("html_utils", "clean_text"),
    "extract_pdf_palette": ("styles", "extract_pdf_palette"),
    "has_class": ("html_utils", "has_class"),
    "hex_to_color": ("styles", "hex_to_color"),
    "make_cover_cropped_image": ("image_layout", "make_cover_cropped_image"),
    "make_styles": ("styles", "make_styles"),
    "make_table": ("story", "make_table"),
    "normalize_crop_focus": ("image_layout", "normalize_crop_focus"),
    "page_background": ("styles", "page_background"),
    "para_text": ("html_utils", "para_text"),
    "render_content_blocks": ("render_content", "render_content_blocks"),
    "render_cover_page": ("render_cover", "render_cover_page"),
    "render_day_section_pdf": ("render_content", "render_day_section_pdf"),
    "render_general_page": ("render_content", "render_general_page"),
    "render_glance_page": ("render_glance", "render_glance_page"),
    "resolve_image_path": ("image_paths", "resolve_image_path"),
    "story_height": ("story", "story_height"),
}


def __getattr__(name: str) -> Any:
    target = _LEGACY_SYMBOL_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(_import_module(f"pdf_exporter_modules.{module_name}"), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LEGACY_SYMBOL_EXPORTS))


__all__ = (
    "PdfExportProfile",
    "PdfExportResult",
    "create_pdf",
    "pdf_export_profile_options",
    "pdf_filename",
    "resolve_pdf_export_profile",
)
