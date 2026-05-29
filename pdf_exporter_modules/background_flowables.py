"""Full-page background image and tint flowables."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable

from .image_layout import make_cover_cropped_image, normalize_crop_focus


class FullPageBackgroundImage(Flowable):
    """Draw an image across the full physical A4 page behind cover text."""

    def __init__(self, source_path, temp_dir, crop_focus="top", page_width=A4[0], page_height=A4[1]):
        super().__init__()
        self.source_path = Path(source_path)
        self.temp_dir = temp_dir
        self.crop_focus = normalize_crop_focus(crop_focus)
        self.page_width = float(page_width)
        self.page_height = float(page_height)

    def wrap(self, availWidth, availHeight):
        return 0, 0.01

    def split(self, availWidth, availHeight):
        return []

    def drawOn(self, canv, x, y, _sW=0):
        cropped_path = make_cover_cropped_image(
            self.source_path,
            self.page_width,
            self.page_height,
            self.temp_dir,
            crop_focus=self.crop_focus,
        )
        if not cropped_path:
            return
        canv.saveState()
        canv.drawImage(
            str(cropped_path),
            0,
            0,
            width=self.page_width,
            height=self.page_height,
            preserveAspectRatio=False,
            mask="auto",
        )
        canv.restoreState()


class FullPageTint(Flowable):
    """Draw a soft full-page tint over a background image for readability."""

    def __init__(self, color=None, alpha=0.72, page_width=A4[0], page_height=A4[1]):
        super().__init__()
        self.color = color or colors.HexColor("#f4efe8")
        self.alpha = float(alpha)
        self.page_width = float(page_width)
        self.page_height = float(page_height)

    def wrap(self, availWidth, availHeight):
        return 0, 0.01

    def split(self, availWidth, availHeight):
        return []

    def drawOn(self, canv, x, y, _sW=0):
        canv.saveState()
        canv.setFillColor(self.color)
        try:
            canv.setFillAlpha(self.alpha)
        except Exception:
            pass
        canv.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)
        canv.restoreState()
