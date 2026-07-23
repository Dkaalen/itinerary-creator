from itinerary_generation.advisor_quality import MAJOR_EDIT, MINOR_EDIT, READY, UNUSABLE, assess_advisor_readiness
from itinerary_generation.client_output_quality_gate import evaluate_client_output_quality
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument


def test_advisor_rating_levels_are_deterministic():
    assert assess_advisor_readiness([]).rating == READY
    assert assess_advisor_readiness([
        ItineraryValidationIssue(WARNING, "missing_confirmed_time", "Missing time")
    ]).rating == MINOR_EDIT
    assert assess_advisor_readiness([
        ItineraryValidationIssue(WARNING, "missing_confirmed_time", "Missing time"),
        ItineraryValidationIssue(WARNING, "missing_confirmed_duration", "Missing duration"),
    ]).rating == MAJOR_EDIT
    assert assess_advisor_readiness([
        ItineraryValidationIssue(BLOCKING, "unsupported_private_claim", "Unsupported private claim")
    ]).rating == UNUSABLE


def test_unsupported_claim_is_blocked_and_weak_fallback_is_reviewable():
    unsupported = RenderDocument(days=[RenderDay(
        day="Day 1", number="1", city="Stavanger", title="Cruise to Bergen",
        intro="Your private transfer takes you to the port.",
        blocks=[RenderBlock(kind="travel", row_id="row-1", source_row_ids=["row-1"], title="Cruise to Bergen")],
    )])
    report = evaluate_client_output_quality(
        unsupported,
        source_rows=[{"row_id": "row-1", "type": "Cruise", "title": "Stavanger to Bergen coastal cruise"}],
    )
    assert report.is_blocked
    assert report.advisor_rating == UNUSABLE
    assert any(issue.code == "unsupported_private_claim" for issue in report.issues)

    fallback = RenderDocument(days=[RenderDay(
        day="Day 1", number="1", city="Bergen", title="Bergen",
        intro="The day’s arrangements are listed below.",
        labels={"intro_decision_source": "admin_fallback_intro"},
    )])
    report = evaluate_client_output_quality(fallback, source_rows=[])
    assert not report.is_blocked
    assert report.advisor_rating == MINOR_EDIT
