from ui.render_cache import make_render_signature


def test_render_signature_is_stable_for_same_content():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    edits = {"trip_title": "Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}

    first = make_render_signature(rows, edits)
    second = make_render_signature(list(rows), dict(edits))

    assert first == second


def test_render_signature_changes_when_preview_content_changes():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    original = {"trip_title": "Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}
    edited = {"trip_title": "Edited Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}

    assert make_render_signature(rows, original) != make_render_signature(rows, edited)


def test_render_signature_ignores_derived_warning_metadata():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    edits = {"trip_title": "Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}
    with_warnings = {
        **edits,
        "latest_client_output_warnings": [{"message": "Review this"}],
        "image_workflow_review": {"warnings": ["weak image"]},
        "day_image_matches": {"Day 1": {"score": 0.9}},
    }

    assert make_render_signature(rows, edits) == make_render_signature(rows, with_warnings)


def test_render_signature_still_changes_for_real_editor_draft_content():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    original = {"editor_draft": {"days": {"Day 1": {"intro": "Welcome."}}}}
    edited = {"editor_draft": {"days": {"Day 1": {"intro": "Edited welcome."}}}}

    assert make_render_signature(rows, original) != make_render_signature(rows, edited)
