"""File export helpers for the itinerary app."""

from pathlib import Path

import streamlit as st

from pdf_exporter import export_html_to_pdf


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
        output_path.write_text(full_html, encoding="utf-8")

        return output_path
    except Exception as error:
        st.error("Could not save the HTML file to disk. The preview still works, but HTML/PDF downloads may not work.")
        with st.expander("HTML save error details"):
            st.exception(error)
        return None


def save_pdf_file(html_path):
    try:
        if not html_path:
            raise ValueError("HTML path is missing. Regenerate the itinerary before creating the PDF.")

        outputs_folder = Path("outputs")
        outputs_folder.mkdir(exist_ok=True)

        pdf_path = outputs_folder / "itinerary_preview.pdf"
        export_html_to_pdf(html_path, pdf_path)

        return pdf_path
    except Exception as error:
        st.error("Could not save the PDF file to disk.")
        with st.expander("PDF save error details"):
            st.exception(error)
        return None
