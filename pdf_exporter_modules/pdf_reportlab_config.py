"""ReportLab runtime configuration for faster itinerary PDF creation."""

from __future__ import annotations


def configure_reportlab_for_fast_pdf() -> None:
    """Use binary image streams instead of slower ASCII85 wrapping.

    ReportLab defaults to ASCII85-encoding embedded image streams in many
    environments.  The itinerary exporter already creates normal PDF files, and
    binary image streams are smaller and much faster for image-heavy documents.
    """

    try:
        from reportlab import rl_config

        rl_config.useA85 = 0
    except Exception:
        # PDF export should continue even if ReportLab changes this setting in a
        # future version or a stripped test environment omits it.
        return


__all__ = ["configure_reportlab_for_fast_pdf"]
