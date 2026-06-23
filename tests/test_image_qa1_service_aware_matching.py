from images.matcher_context import build_day_context
from images.matcher_scoring import score_image_for_day
from images.metadata import ImageCandidate


def _candidate(city, filename, *, themes=(), tokens=(), country="Norway"):
    return ImageCandidate(
        path=f"/bank/{city}/{filename}.jpg",
        country=country,
        city=city,
        filename=f"{filename}.jpg",
        tokens=tuple(tokens),
        themes=tuple(themes),
        seasons=("autumn",),
    )


def test_image_qa1_train_day_prefers_rail_image_over_cliff_city_fallback():
    context = build_day_context("Day 5", [
        {"day": "Day 5", "type": "Train", "effective_type": "Train", "city": "Kristiansand", "title": "Scenic train transfer to Stavanger", "details": "Time: 12:00 pm - 3:18 pm"},
    ])

    rail = _candidate("Kristiansand", "kristiansand-railway-train", themes=("train",), tokens=("train", "railway", "station"))
    city = _candidate("Kristiansand", "kristiansand-city-streets", themes=("city",), tokens=("city", "streets"))

    rail_score, rail_reasons = score_image_for_day(rail, context)
    city_score, city_reasons = score_image_for_day(city, context)

    assert "rail" in context["service_intents"]
    assert rail_score > city_score
    assert any("service intent match" in reason for reason in rail_reasons)
    assert any("generic city image downranked" in reason for reason in city_reasons)


def test_image_qa1_nutshell_context_allows_route_places_and_fjord_rail_visuals():
    context = build_day_context("Day 9", [
        {"day": "Day 9", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "title": "Norway in a Nutshell to Oslo", "details": "Bergen to Voss, Gudvangen to Flåm, Myrdal to Oslo"},
    ])

    flam = _candidate("Flåm", "flam-rail-fjord", themes=("train", "fjord", "mountain"), tokens=("flam", "rail", "fjord"))
    oslo = _candidate("Oslo", "oslo-city-skyline", themes=("city",), tokens=("oslo", "city", "skyline"))

    flam_score, _ = score_image_for_day(flam, context)
    oslo_score, _ = score_image_for_day(oslo, context)

    assert {"scenic_rail_fjord", "rail", "fjord_cruise"} <= context["service_intents"]
    assert "flam" in context["city_variants"]
    assert flam_score > oslo_score
