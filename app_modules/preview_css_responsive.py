"""Preview/PDF print and responsive styles."""

CSS = r"""
@media print {
            @page {
                size: A4 portrait;
                margin: 0;
            }

            .preview-background {
                background: white;
                padding: 0;
            }

            .a4-page {
                width: 210mm;
                height: 297mm;
                min-height: 297mm;
                margin: 0;
                box-shadow: none;
                break-after: page;
                page-break-after: always;
            }
        }
"""
