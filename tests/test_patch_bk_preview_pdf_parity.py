from reportlab.platypus import KeepTogether, Spacer

from itinerary_generation.client_sanitizer import sanitize_client_text
from pdf_exporter_modules.story import add_bullets
from pdf_exporter_modules.styles import make_styles


def test_client_sanitizer_removes_clipboard_fragment_markers():
    assert sanitize_client_text("Included journey: StartFragmentBergen RailwayEndFragment") == "Included journey: Bergen Railway"


def test_pdf_bullet_items_keep_multiline_inclusion_details_together():
    story = []
    add_bullets(
        story,
        ["Flight from Bergen to Tromsø\n2:45 PM - 4:30 PM\nTickets and Luggage included"],
        make_styles(),
    )

    keepers = [flowable for flowable in story if isinstance(flowable, KeepTogether)]
    assert len(keepers) == 1
    assert isinstance(story[-1], Spacer)
