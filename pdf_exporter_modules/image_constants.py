"""PDF image layout constants."""

from reportlab.lib.units import mm

PDF_IMAGE_GAP = 15  # approximately 20 CSS pixels
PDF_IMAGE_HALF_OFFSET = 7.5  # approximately 10 CSS pixels
PDF_MIN_IMAGE_HEIGHT = 40 * mm
PDF_CROP_VERTICAL_FOCUS = 0.25  # protect upper/sky detail when vertical cropping is needed
PDF_CROP_FOCUS_FACTORS = {
    "top": 0.18,
    "center": 0.50,
    "bottom": 0.82,
}
PDF_IMAGE_BOTTOM_Y = 0  # day images bleed to the physical lower page edge
