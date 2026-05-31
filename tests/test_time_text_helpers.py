from time_duration import format_duration_display
from time_text import clean_time_text


def test_clean_time_text_is_shared_by_duration_display():
    assert clean_time_text(" 5. 5\xa0Hrs ") == "5.5 Hrs"
    assert format_duration_display("Duration: 5. 5 Hrs") == "5 hours 30 minutes"
