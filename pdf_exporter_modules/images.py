from pathlib import Path

try:
    from PIL import Image as PILImage, ImageOps
except Exception:  # pragma: no cover - export safely skips images if Pillow is unavailable
    PILImage = None
    ImageOps = None

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Flowable

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


def resolve_image_path(raw_path, html_path):
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = (Path(html_path).parent / path).resolve()
    if path.exists() and path.is_file():
        return path
    return None


def calculate_day_image_layout(
    used_height,
    content_height,
    gap=PDF_IMAGE_GAP,
    half_offset=PDF_IMAGE_HALF_OFFSET,
    min_height=PDF_MIN_IMAGE_HEIGHT,
    bottom_bleed=0,
):
    """Return spacer/image height for lower-half day imagery, or None."""
    image_top = max(float(used_height) + float(gap), (float(content_height) / 2.0) + float(half_offset))
    image_height = float(content_height) + float(bottom_bleed) - image_top
    if image_height < float(min_height):
        return None
    spacer_height = max(0, image_top - float(used_height))
    return spacer_height, image_height


def normalize_crop_focus(value):
    value = str(value or "").strip().lower()
    if value in PDF_CROP_FOCUS_FACTORS:
        return value
    if value in {"upper", "sky", "aurora"}:
        return "top"
    if value in {"lower"}:
        return "bottom"
    return "top"


def make_cover_cropped_image(source_path, target_width, target_height, temp_dir, crop_focus="top"):
    """Create a temporary cover-cropped image matching the PDF box ratio."""
    if PILImage is None or ImageOps is None:
        return None

    try:
        with PILImage.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            source_width, source_height = image.size
            if source_width <= 0 or source_height <= 0 or target_width <= 0 or target_height <= 0:
                return None

            target_ratio = float(target_width) / float(target_height)
            source_ratio = float(source_width) / float(source_height)

            if source_ratio > target_ratio:
                crop_width = max(1, int(source_height * target_ratio))
                left = max(0, int((source_width - crop_width) / 2))
                box = (left, 0, min(source_width, left + crop_width), source_height)
            else:
                crop_height = max(1, int(source_width / target_ratio))
                extra_height = max(0, source_height - crop_height)
                focus = PDF_CROP_FOCUS_FACTORS.get(normalize_crop_focus(crop_focus), PDF_CROP_VERTICAL_FOCUS)
                top = max(0, int(extra_height * focus))
                box = (0, top, source_width, min(source_height, top + crop_height))

            image = image.crop(box)
            temp_path = Path(temp_dir) / (
                f"day_image_{abs(hash((str(source_path), round(float(target_width), 2), round(float(target_height), 2), normalize_crop_focus(crop_focus)))) % 10_000_000}.jpg"
            )
            image.save(temp_path, format="JPEG", quality=88, optimize=True)
            return temp_path
    except Exception:
        return None


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
        # ReportLab can reset transparency when a new fill color is applied,
        # so set the alpha after the color. This keeps summary-page seasonal
        # artwork visible under the readability wash in exported PDFs.
        try:
            canv.setFillAlpha(self.alpha)
        except Exception:
            pass
        canv.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)
        canv.restoreState()


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
        divider_color = colors.HexColor("#b89555")
        # Draw one clean, solid divider with its vertical center aligned to the
        # top edge of the image. The decorative emblem is intentionally omitted
        # for a cleaner day-page transition.
        canv.setStrokeColor(divider_color)
        canv.setLineWidth(5.0)
        canv.line(self.absolute_x, image_top_y, self.absolute_x + self.content_width, image_top_y)
        canv.restoreState()


def add_day_image_if_possible(
    page,
    page_story,
    html_path,
    temp_dir,
    available_width,
    available_height,
    measurement_story=None,
    left_margin=0,
    top_margin=0,
):
    """Add a same-page lower-half edge-to-edge day image when a match exists."""
    slot = page.select_one(".day-image-slot")
    if not slot:
        return

    image_path = resolve_image_path(slot.get("data-image-path"), html_path)
    if not image_path:
        return

    crop_focus = normalize_crop_focus(slot.get("data-image-crop-focus", "top"))

    page_story.append(
        SamePageDayImage(
            source_path=image_path,
            temp_dir=temp_dir,
            x=0,
            content_top_y=A4[1] - top_margin,
            content_width=A4[0],
            content_height=available_height,
            page_height=A4[1],
            bottom_y=PDF_IMAGE_BOTTOM_Y,
            crop_focus=crop_focus,
        )
    )
