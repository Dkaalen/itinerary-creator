import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_exporter import calculate_day_image_layout, export_html_to_pdf, make_cover_cropped_image
from reportlab.lib.units import mm


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label}\nExpected: {expected!r}\nActual:   {actual!r}"
        )


def count_pdf_pages(pdf_path):
    content = Path(pdf_path).read_bytes()
    return content.count(b"/Type /Page") - content.count(b"/Type /Pages")

def test_pdf_day_image_layout_rules():
    content_height = 720
    minimum = 40 * mm

    light_day_layout = calculate_day_image_layout(
        used_height=120,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
    )
    if not light_day_layout:
        raise AssertionError("Light days should have room for a lower-half image.")
    spacer, image_height = light_day_layout
    assert_equal(
        round(120 + spacer, 1),
        367.5,
        "Image should not start above the halfway point plus offset.",
    )
    if image_height < minimum:
        raise AssertionError("Image height should respect the minimum height threshold.")

    bleed_layout = calculate_day_image_layout(
        used_height=120,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
        bottom_bleed=62.4,
    )
    if not bleed_layout:
        raise AssertionError("Bottom-bleed image layout should still be allowed when there is room.")
    _, bleed_image_height = bleed_layout
    if bleed_image_height <= image_height:
        raise AssertionError("Bottom-bleed images should extend below the normal content area to the page edge.")

    heavy_day_layout = calculate_day_image_layout(
        used_height=650,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
    )
    assert_equal(
        heavy_day_layout,
        None,
        "Text-heavy days should skip images when there is not enough usable space.",
    )


def test_pdf_export_places_day_image_from_current_page_story():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        image_path = tmp_path / "Oslo_Test_Image.jpg"
        image = Image.new("RGB", (320, 190))
        pixels = image.load()
        for x in range(320):
            for y in range(190):
                pixels[x, y] = (x % 256, y % 256, (x * y) % 256)
        image.save(image_path, format="JPEG", quality=88)

        html_path = tmp_path / "preview.html"
        pdf_path = tmp_path / "preview.pdf"
        html_content = (
            '<html><body>'
            '<div class="a4-page cover-page">'
            '<div class="cover-kicker">Curated Travel Itinerary</div>'
            '<div class="cover-title">Image Test</div>'
            '</div>'
            '<div class="a4-page day-page single-day-page" data-day="Day 1">'
            '<section class="day-section">'
            '<div class="day-label">Day 1</div>'
            '<div class="day-title">Oslo Image Test</div>'
            '<div class="city">Oslo</div>'
            '<div class="intro">A short Oslo day with enough room for a lower-half image.</div>'
            '<div class="content-block"><div class="block-heading">Morning Experience</div><div class="block-title">Oslo City Walk</div></div>'
            '</section>'
            f'<div class="day-image-slot" data-image-path="{image_path}"></div>'
            '</div>'
            '</body></html>'
        )
        html_path.write_text(html_content, encoding="utf-8")

        export_html_to_pdf(html_path, pdf_path)
        if pdf_path.stat().st_size < 10_000:
            raise AssertionError("PDF day image should be inserted when the current page has enough room.")
        assert_equal(
            count_pdf_pages(pdf_path),
            2,
            "Day image rendering should not create an image-only continuation page.",
        )

        try:
            import fitz
        except Exception as exc:  # pragma: no cover - local dependency guard
            raise AssertionError(f"PyMuPDF/fitz is required for rendered PDF image smoke checks: {exc}")

        document = fitz.open(pdf_path)
        try:
            day_page = document.load_page(1)
            pixmap = day_page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            bottom_center = pixmap.pixel(pixmap.width // 2, pixmap.height - 1)
            page_bg = (244, 239, 232)
            if sum(abs(int(bottom_center[i]) - page_bg[i]) for i in range(3)) < 20:
                raise AssertionError("Day image should touch the physical lower page edge, not stop above the margin.")
        finally:
            document.close()


def test_cover_crop_protects_upper_image_content():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "Aurora_Portrait.jpg"
        image = Image.new("RGB", (100, 300), (0, 0, 180))
        pixels = image.load()
        for x in range(100):
            for y in range(300):
                if y < 80:
                    pixels[x, y] = (0, 220, 80)  # bright upper sky detail
                elif y > 220:
                    pixels[x, y] = (80, 45, 20)
        image.save(source_path, format="JPEG", quality=95)

        cropped_path = make_cover_cropped_image(source_path, 400, 200, tmp_path)
        if not cropped_path:
            raise AssertionError("Cover crop should create a temporary image.")

        with Image.open(cropped_path) as cropped:
            top_pixel = cropped.getpixel((cropped.width // 2, 5))
            if top_pixel[1] < 120:
                raise AssertionError(
                    "Vertical cover crop should preserve upper sky/aurora detail better than a center crop."
                )



def test_cover_crop_focus_options_change_vertical_crop():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "Tall_Image.jpg"
        image = Image.new("RGB", (100, 300), (0, 0, 0))
        pixels = image.load()
        for x in range(100):
            for y in range(300):
                if y < 80:
                    pixels[x, y] = (0, 220, 80)
                elif y > 220:
                    pixels[x, y] = (220, 60, 20)
                else:
                    pixels[x, y] = (20, 20, 180)
        image.save(source_path, format="JPEG", quality=95)

        top_path = make_cover_cropped_image(source_path, 400, 200, tmp_path, crop_focus="top")
        bottom_path = make_cover_cropped_image(source_path, 400, 200, tmp_path, crop_focus="bottom")
        if not top_path or not bottom_path:
            raise AssertionError("Cover crop should create focus-specific temporary images.")

        with Image.open(top_path) as top_crop, Image.open(bottom_path) as bottom_crop:
            top_pixel = top_crop.getpixel((top_crop.width // 2, 5))
            bottom_pixel = bottom_crop.getpixel((bottom_crop.width // 2, bottom_crop.height - 5))
            if top_pixel[1] < 120:
                raise AssertionError("Top crop focus should keep upper sky/aurora detail visible.")
            if bottom_pixel[0] < 120:
                raise AssertionError("Bottom crop focus should keep lower foreground detail visible.")





def run_all():
    tests = [
        test_pdf_day_image_layout_rules,
        test_pdf_export_places_day_image_from_current_page_story,
        test_cover_crop_protects_upper_image_content,
        test_cover_crop_focus_options_change_vertical_crop,
    ]

    for test in tests:
        test()

    print(f"All PDF tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
