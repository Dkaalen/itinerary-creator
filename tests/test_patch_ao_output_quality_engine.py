from __future__ import annotations

from pathlib import Path

from PIL import Image

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import create_journey_arc, create_trip_title, group_rows_by_day
from images.image_bank import get_image_bank_paths
from images.matcher_selection import select_day_image
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_generation.render_model import RenderBlock, RenderDocument, RenderFinalPage, RenderFinalSection, RenderMetaLine, RenderSummary, RenderDay
from itinerary_generation.summaries import sanitize_journey_arc_experience
from itinerary_parser import normalize_time_text, parse_itinerary
from normalizer import normalize_itinerary_rows
from text_polish import polish_client_text
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES


def _rows(raw: str) -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_important_travel_notes_stay_typed_paragraphs_in_render_document():
    rows = _rows(
        """
Day 1	Activity		01/01/2026		09:00 AM	2 hours			Oslo	Oslo Walking Tour
        """
    )
    grouped = group_rows_by_day(rows)

    context = build_itinerary_render_context(rows, grouped, {})
    notes_sections = [section for section in context.render_document.final_sections if section.section_id == "important_travel_notes"]

    assert notes_sections
    paragraphs = notes_sections[0].pages[0].paragraphs
    assert paragraphs == list(DEFAULT_IMPORTANT_TRAVEL_NOTES)
    assert not any(paragraph.startswith("[") or paragraph.endswith("]") for paragraph in paragraphs)


def test_image_bank_paths_include_user_sibling_full_bank_before_local_fallback(tmp_path):
    app_root = tmp_path / "itinerary-creator-git"
    sibling_bank = tmp_path / "image_bank_full"
    local_fallback = app_root / "image_bank"
    sibling_bank.mkdir(parents=True)
    local_fallback.mkdir(parents=True)

    paths = get_image_bank_paths(app_root)

    assert paths[0] == sibling_bank
    assert local_fallback in paths


def test_journey_arc_forbidden_phrases_are_sanitized_and_not_generated():
    assert sanitize_journey_arc_experience("Aurora, Santa Village and Arctic experiences") == "Northern Lights, Santa Village and Arctic experiences"
    assert sanitize_journey_arc_experience("Onward flight", chapter="Bergen") == "Welcome to Bergen"
    assert sanitize_journey_arc_experience("Onward travel", chapter="Oslo") == "Welcome to Oslo"

    rows = _rows(
        """
Day 1	Activity		01/01/2026		20:00	3 hours			Tromsø	Aurora photography tour
Day 2	Flight		02/01/2026		10:00 AM				Tromsø	Flight from Tromsø to Oslo
        """
    )
    arc_text = "\n".join(row["experience"] for row in create_journey_arc(group_rows_by_day(rows)))

    assert "Aurora" not in arc_text
    assert "Onward flight" not in arc_text
    assert "Onward travel" not in arc_text
    assert "Northern Lights" in arc_text

    title_rows = _rows(
        """
Day 1	Activity		01/01/2026		20:00	3 hours			Kiruna	Aurora hunt and Icehotel visit
        """
    )
    trip_title = create_trip_title(title_rows, group_rows_by_day(title_rows))
    assert "Aurora" not in trip_title
    assert "Northern Lights" in trip_title


def test_client_output_quality_gate_blocks_ao_forbidden_output():
    document = RenderDocument(
        summary=RenderSummary(journey_arc=[{"chapter": "Tromsø", "days": "1", "experience": "Aurora and Onward flight"}]),
        days=[
            RenderDay(
                day="Day 1",
                number="1",
                city="Tromsø",
                title="Tromsø",
                intro="Supplier text (if snow)",
                blocks=[
                    RenderBlock(
                        kind="activity",
                        title="Bare activity heading",
                        meta=[RenderMetaLine("Time", "15 min. before departure. Bring warm clothes.")],
                    )
                ],
            )
        ],
        final_sections=[RenderFinalSection("notes", "Notes", pages=[RenderFinalPage(paragraphs=["Raw What's included section leaked to Airport"])])],
    )

    report = evaluate_client_output_quality(
        document,
        day_images={"Day 1": {"city": "Default", "filename": "Default_Winter_01", "is_default": True, "stronger_candidate_available": True}},
    )
    codes = {issue.code for issue in report.blocking_issues}

    assert report.is_blocked
    assert "forbidden_aurora_wording" in codes
    assert "forbidden_onward_flight" in codes
    assert "supplier_parenthetical_if_snow" in codes
    assert "rough_airport_wording" in codes
    assert "supplier_warning_in_time_field" in codes
    assert "bare_activity_inclusion_heading" in codes
    assert "raw_supplier_field_leak" in codes
    assert "default_image_used_despite_stronger_match" not in codes


def test_supplier_junk_parentheticals_and_time_warnings_are_cleaned_generically():
    assert polish_client_text("Thermal suit (unlimited) and snowmobile route (if snow)") == "Thermal suit and snowmobile route"
    assert polish_client_text("Private transfer to Airport") == "Private transfer to the airport"
    assert normalize_time_text("15 min. before departure. Bring warm clothes.") == ""
    assert normalize_time_text("08:30 AM. Please arrive 15 min. before departure.") == "8:30 AM"


def test_tallinn_day_intro_and_ferry_description_focus_on_old_town_experience():
    rows = _rows(
        """
Day 1	Activity		01/06/2026						Helsinki	Excursion to Tallinn - Departure from Helsinki: 10:30 am - Return from Tallinn: 7:30 pm - Ferry tickets included
Day 1	Activity		01/06/2026		13:00	2 hours			Tallinn	Old Town Guided Tour
        """
    )
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {})
    day = context.render_document.days[0]
    text = "\n".join([day.intro, *[block.description for block in day.blocks]])

    assert "Old Town" in text
    assert "ferry crossings" in text or "ferry" in text
    assert "Guided sightseeing is shown separately" in text
    assert "Today combines complementary experiences in Helsinki" not in day.intro


def test_selected_image_payload_exposes_explainable_score_breakdown(tmp_path):
    bank = tmp_path / "image_bank_full"
    (bank / "Norway" / "Oslo").mkdir(parents=True)
    (bank / "Default").mkdir(parents=True)
    Image.new("RGB", (40, 25), (40, 100, 140)).save(bank / "Norway" / "Oslo" / "Oslo_Walking_Tour_Summer_01.webp", format="WEBP")
    Image.new("RGB", (40, 25), (80, 80, 80)).save(bank / "Default" / "Default_Summer_City_01.webp", format="WEBP")
    rows = _rows(
        """
Day 1	Activity		01/06/2026		09:00 AM	2 hours			Oslo	Oslo Walking Tour
        """
    )

    match = select_day_image("Day 1", rows, bank)

    assert match
    assert match["city"] == "Oslo"
    assert match["is_default"] is False
    assert match["fallback_reason"] == ""
    assert match["score_breakdown"]["destination_score"] >= 60
    assert match["score_breakdown"]["activity_product_score"] >= 1
    assert "season_score" in match["score_breakdown"]
    assert match["score_breakdown"]["total_score"] == match["score"]


def test_default_image_payload_proves_no_stronger_match_when_only_default_exists(tmp_path):
    bank = tmp_path / "image_bank_full"
    (bank / "Default").mkdir(parents=True)
    Image.new("RGB", (40, 25), (80, 80, 80)).save(bank / "Default" / "Default_Summer_City_01.webp", format="WEBP")
    rows = _rows(
        """
Day 1	Activity		01/06/2026		09:00 AM	2 hours			Oslo	Oslo Walking Tour
        """
    )

    match = select_day_image("Day 1", rows, bank)

    assert match
    assert match["is_default"] is True
    assert match["stronger_candidate_available"] is False
    assert match["audit"]["fallback_proof"] == "no stronger unused destination/activity match available"
    assert match["audit"]["best_non_default_score"] == 0
