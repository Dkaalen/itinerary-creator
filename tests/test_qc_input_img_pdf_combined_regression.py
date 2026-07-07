from images.destination_image_library import image_library_day_rows
from images.image_workflow_review import build_image_workflow_review
from itinerary_generation.input_review import build_structured_input_review, format_structured_input_review
from itinerary_generation.itinerary_health_checks import build_itinerary_health_issues
from itinerary_parser import parse_itinerary
from pdf_exporter_modules.export_profiles import pdf_filename, resolve_pdf_export_profile


def test_stab_qc_flags_duplicates_heavy_days_and_route_backtrack():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "hotel_name": "Hotel A", "commercial_status": "included"},
        {"day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "Walking Tour", "details": "Guided walk", "commercial_status": "included"},
        {"day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "Walking Tour", "details": "Guided walk", "commercial_status": "included"},
        {"day": "Day 2", "type": "Hotel", "effective_type": "Hotel", "city": "Bergen", "hotel_name": "Hotel B", "commercial_status": "included"},
        {"day": "Day 3", "type": "Transfer", "effective_type": "Transfer", "city": "Oslo", "title": "Private transfer from Bergen to Oslo", "details": "Private transfer from Bergen to Oslo", "commercial_status": "included"},
    ]

    codes = {issue.code for issue in build_itinerary_health_issues(rows)}

    assert "duplicate_service" in codes
    assert "route_backtrack" in codes


def test_parser_extracts_route_points_and_confidence_flags():
    raw = "Day 1\tTransfer\tTrain Oslo to Bergen - Departure 08:00\nDay 2\tHotel\tBergen: Check in for a 2 night stay - Hotel Norge - Deluxe Room - Breakfast"

    rows = parse_itinerary(raw)
    transfer = rows[0]
    hotel = rows[1]

    assert transfer["effective_type"] == "Train"
    assert transfer["route_origin"] == "Oslo"
    assert transfer["route_destination"] == "Bergen"
    assert transfer["parser_confidence"] >= 80
    assert "missing_city" not in transfer["parser_review_flags"]
    assert hotel["hotel_name"] == "Hotel Norge"
    assert "parser_review_flags" in hotel


def test_structured_input_review_surfaces_parser_confidence_flags():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "commercial_status": "included", "parser_confidence": 55, "parser_review_flags": ["missing_hotel_name"]},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "title": "Museum", "commercial_status": "included", "parser_confidence": 100, "parser_review_flags": []},
    ]

    review = build_structured_input_review(rows)
    text = format_structured_input_review(review)

    assert review.average_confidence == 78
    assert review.review_flags == {"missing_hotel_name": 1}
    assert "Parser confidence: 78%" in text
    assert "Review flags: missing_hotel_name: 1" in text


def test_img2_image_review_marks_fallback_and_replacement_options():
    grouped_days = {"Day 1": [{"city": "Oslo"}], "Day 2": [{"city": "Bergen"}]}
    matches = {
        "Day 1": {"path": "/bank/default/oslo.jpg", "is_default": True, "score": 40},
        "Day 2": {"path": "/bank/bergen.jpg", "score": 80},
    }
    replacements = {"Day 1": [{"path": "/bank/oslo-1.jpg"}, {"path": "/bank/oslo-2.jpg"}]}

    review = build_image_workflow_review(grouped_days, matches, replacement_options_by_day=replacements)
    library_rows = image_library_day_rows(grouped_days, matches, replacements)

    assert review.status_label == "Review"
    assert review.low_quality_days == ("Day 1",)
    assert review.replacement_option_count == 2
    assert library_rows[0].status == "fallback"
    assert library_rows[0].replacement_options == 2


def test_pdf2_export_profiles_have_safe_filenames_and_profiles():
    default = resolve_pdf_export_profile(None)
    compact = resolve_pdf_export_profile("client_compact")
    internal = resolve_pdf_export_profile({"pdf_export_profile": "internal_review"})

    assert default.id == "client_premium"
    assert compact.min_compact_level == 1
    assert internal.include_internal_notes is True
    assert pdf_filename(profile={"id": "client_compact"}) == "itinerary_preview_compact.pdf"
    assert pdf_filename(profile={"id": "internal_review"}) == "itinerary_preview_internal.pdf"
