"""File export helpers for the itinerary app."""

from pathlib import Path

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - lightweight test/runtime fallback
    class _NoStreamlit:
        def error(self, *_args, **_kwargs):
            return None

        def exception(self, *_args, **_kwargs):
            return None

        class _Expander:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        def expander(self, *_args, **_kwargs):
            return self._Expander()

    st = _NoStreamlit()

from pdf_exporter_modules.export_profiles import pdf_filename, resolve_pdf_export_profile
from pdf_exporter import export_html_to_pdf, export_render_document_to_pdf, render_document_requires_html_fallback


def build_full_html_document(itinerary_html):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Itinerary Preview</title>
</head>
<body style="margin: 0;">
{itinerary_html}
</body>
</html>
"""


def save_html_file(itinerary_html):
    try:
        outputs_folder = Path("outputs")
        outputs_folder.mkdir(exist_ok=True)

        output_path = outputs_folder / "itinerary_preview.html"
        full_html = build_full_html_document(itinerary_html)
        if output_path.exists():
            try:
                if output_path.read_text(encoding="utf-8") == full_html:
                    return output_path
            except OSError:
                pass
        output_path.write_text(full_html, encoding="utf-8")

        return output_path
    except Exception as error:
        st.error("Could not save the HTML file to disk. The preview still works, but HTML/PDF downloads may not work.")
        with st.expander("HTML save error details"):
            st.exception(error)
        return None


def save_pdf_file(html_path, *, render_document=None, color_data=None, day_images=None, day_image_crop_focus=None, output_edits=None):
    try:
        if not html_path:
            raise ValueError("HTML path is missing. Regenerate the itinerary before creating the PDF.")

        outputs_folder = Path("outputs")
        outputs_folder.mkdir(exist_ok=True)

        profile = resolve_pdf_export_profile(output_edits or None)
        base_name = "itinerary_preview_booknordics" if str((output_edits or {}).get("output_brand") or "agent") == "booknordics_customer" else "itinerary_preview"
        pdf_path = outputs_folder / pdf_filename(base_name=base_name, profile=profile.as_dict())
        if render_document is not None and not render_document_requires_html_fallback(render_document, output_edits):
            export_render_document_to_pdf(
                render_document,
                pdf_path,
                color_data=color_data,
                day_images=day_images,
                day_image_crop_focus=day_image_crop_focus,
                export_profile=profile.as_dict(),
                output_brand=str((output_edits or {}).get("output_brand") or "agent"),
            )
        else:
            export_html_to_pdf(html_path, pdf_path)

        return pdf_path
    except Exception as error:
        st.error("Could not save the PDF file to disk.")
        with st.expander("PDF save error details"):
            st.exception(error)
        return None
