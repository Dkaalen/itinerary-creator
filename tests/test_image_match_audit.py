from pathlib import Path
import tempfile

from images.day_image_ui import render_day_image_slot
from images.image_match_audit import audit_day_image_matches


def test_manual_protected_specialty_image_is_blocked_for_unrelated_day():
    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        image_path = default_dir / "Default_Winter_Polar_Icebreaker_01.webp"
        image_path.write_bytes(b"fake image")

        grouped = {
            "Day 3": [
                {
                    "day": "Day 3",
                    "type": "Hotel",
                    "effective_type": "Hotel",
                    "city": "Rovaniemi",
                    "title": "Scandic Rovaniemi City",
                    "date": "29/10/2026",
                }
            ]
        }
        matches = {"Day 3": {"path": str(image_path), "score": 999, "reason": "manual image selection"}}
        output_edits = {"day_images": {"Day 3": {"mode": "manual", "path": str(image_path)}}}

        warnings = audit_day_image_matches(grouped, matches, output_edits=output_edits, image_bank_scan_paths=bank)

        assert any(warning.code == "image_protected_specialty_mismatch" for warning in warnings)
        assert any(warning.severity == "error" for warning in warnings)


def test_manual_wrong_destination_image_is_review_warning_not_silent():
    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        oslo_dir = bank / "Norway" / "Oslo"
        oslo_dir.mkdir(parents=True)
        image_path = oslo_dir / "Oslo_Opera_House_01.webp"
        image_path.write_bytes(b"fake image")

        grouped = {
            "Day 5": [
                {
                    "day": "Day 5",
                    "type": "Activity",
                    "effective_type": "Activity",
                    "city": "Bergen",
                    "title": "Bergen harbour walking tour",
                    "details": "Bryggen waterfront and city centre walk.",
                }
            ]
        }
        matches = {"Day 5": {"path": str(image_path), "score": 999, "reason": "manual image selection"}}
        output_edits = {"day_images": {"Day 5": {"mode": "manual", "path": str(image_path)}}}

        warnings = audit_day_image_matches(grouped, matches, output_edits=output_edits, image_bank_scan_paths=bank)

        assert any(warning.code == "manual_image_destination_mismatch" for warning in warnings)
        assert not any(warning.severity == "error" for warning in warnings)


def test_day_image_slot_carries_source_and_match_metadata_without_visible_text():
    html = render_day_image_slot(
        "Day 7",
        [
            {
                "row_id": "source-row-7a",
                "day": "Day 7",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Tromso",
                "title": "Photo Tour to Arctic Landscapes and Fjords",
            }
        ],
        match={
            "path": "/tmp/Tromso_Fjord_View.webp",
            "score": 96,
            "reason": "city folder match; theme match: fjord",
            "city": "Tromso",
            "themes": ["fjord", "mountain"],
        },
        output_edits={},
        image_bank_scan_paths="missing",
    )

    assert 'data-source-row-ids="source-row-7a"' in html
    assert 'data-image-city="Tromso"' in html
    assert 'data-image-themes="fjord,mountain"' in html
    assert "source-row-7a" not in html.split(">", 1)[-1]
