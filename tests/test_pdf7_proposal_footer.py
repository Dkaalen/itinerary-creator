from types import SimpleNamespace

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from pdf_exporter_modules.styles import draw_proposal_footer, page_background


class RecordingCanvas:
    def __init__(self):
        self.calls = []

    def saveState(self):
        self.calls.append(("saveState",))

    def restoreState(self):
        self.calls.append(("restoreState",))

    def setFillColor(self, color):
        self.calls.append(("setFillColor", color))

    def setStrokeColor(self, color):
        self.calls.append(("setStrokeColor", color))

    def setLineWidth(self, width):
        self.calls.append(("setLineWidth", width))

    def setFont(self, font_name, font_size):
        self.calls.append(("setFont", font_name, font_size))

    def rect(self, *args, **kwargs):
        self.calls.append(("rect", args, kwargs))

    def line(self, *args):
        self.calls.append(("line", args))

    def drawString(self, *args):
        self.calls.append(("drawString", args))

    def drawRightString(self, *args):
        self.calls.append(("drawRightString", args))


def _doc(page=2, title="Client PDF"):
    return SimpleNamespace(
        page=page,
        title=title,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        bottomMargin=22 * mm,
    )


def test_pdf7_footer_is_hidden_on_cover_page():
    canvas = RecordingCanvas()

    draw_proposal_footer(canvas, _doc(page=1))

    assert not any(call[0] == "line" for call in canvas.calls)
    assert not any(call[0] == "drawRightString" for call in canvas.calls)


def test_pdf7_footer_stays_removed_after_cover():
    canvas = RecordingCanvas()

    draw_proposal_footer(canvas, _doc(page=4))

    assert not any(call[0] == "line" for call in canvas.calls)
    assert not any(call[0] == "drawString" for call in canvas.calls)
    assert not any(call[0] == "drawRightString" for call in canvas.calls)


def test_pdf7_page_background_keeps_background_without_footer_after_cover():
    canvas = RecordingCanvas()

    page_background(canvas, _doc(page=2, title="Nordic Proposal"))

    call_names = [call[0] for call in canvas.calls]
    assert "rect" in call_names
    assert "line" not in call_names
    assert not any(call[0] == "drawString" for call in canvas.calls)
