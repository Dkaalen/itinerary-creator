from itinerary_generation.content_validator import validate_html


def test_destination_food_validator_does_not_match_across_final_summary_sections():
    html = """
    <section class="day-section" data-day="Day 19">
      <div class="day-title">Departure from Oslo</div>
      <div class="body-text">Private transfer to Oslo Airport.</div>
    </section>
    <div class="final-list-page">
      <h2>What’s included</h2>
      <div>Accommodation</div><div>The Thief, Oslo</div>
      <div>Activities</div><div>Copenhagen Food Tour with smørrebrød and Danish meatballs.</div>
    </div>
    """

    assert [finding.code for finding in validate_html(html)] == []


def test_destination_food_validator_still_catches_same_day_mismatch():
    html = """
    <section class="day-section" data-day="Day 18">
      <div class="day-title">Oslo Food Tour</div>
      <div class="body-text">Taste smørrebrød and Danish meatballs during the Oslo food tour.</div>
    </section>
    """

    assert "wrong_oslo_danish_food" in [finding.code for finding in validate_html(html)]
