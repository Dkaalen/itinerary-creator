"""Day-page image flowable for PDF exports."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable

from pdf_exporter_modules import pdf_style_tokens as tokens
from pdf_exporter_modules.pdf_branding import is_booknordics_pdf

from .image_constants import PDF_IMAGE_BOTTOM_Y, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT
from .image_layout import make_cover_cropped_image, normalize_crop_focus


class SamePageDayImage(Flowable):
    """Draw a day image on the current A4 page without creating a new page."""

    def __init__(
        self,
        source_path,
        temp_dir,
        x,
        content_top_y,
        content_width,
        content_height,
        page_height=A4[1],
        bottom_y=PDF_IMAGE_BOTTOM_Y,
        gap=PDF_IMAGE_GAP,
        half_offset=PDF_IMAGE_HALF_OFFSET,
        min_height=PDF_MIN_IMAGE_HEIGHT,
        crop_focus="top",
    ):
        super().__init__()
        self.source_path = Path(source_path)
        self.temp_dir = temp_dir
        self.absolute_x = float(x)
        self.content_top_y = float(content_top_y)
        self.content_width = float(content_width)
        self.content_height = float(content_height)
        self.page_height = float(page_height)
        self.bottom_y = float(bottom_y)
        self.gap = float(gap)
        self.half_offset = float(half_offset)
        self.min_height = float(min_height)
        self.crop_focus = normalize_crop_focus(crop_focus)

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def split(self, availWidth, availHeight):
        return []

    def drawOn(self, canv, x, y, _sW=0):
        text_bottom_y = float(y)
        image_top_y = min(
            text_bottom_y - self.gap,
            (self.page_height / 2.0) - self.half_offset,
        )
        image_height = image_top_y - self.bottom_y
        if image_height < self.min_height:
            return

        cropped_path = make_cover_cropped_image(
            self.source_path,
            self.content_width,
            image_height,
            self.temp_dir,
            crop_focus=self.crop_focus,
        )
        if not cropped_path:
            return

        canv.saveState()
        canv.drawImage(
            str(cropped_path),
            self.absolute_x,
            self.bottom_y,
            width=self.content_width,
            height=image_height,
            preserveAspectRatio=False,
            mask="auto",
        )
        divider_color = tokens.ACCENT if is_booknordics_pdf() else colors.HexColor("#b89555")
        canv.setStrokeColor(divider_color)
        canv.setLineWidth(5.0)
        canv.line(self.absolute_x, image_top_y, self.absolute_x + self.content_width, image_top_y)
        canv.restoreState()
