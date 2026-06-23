from app_modules.export_state import export_readiness_from_state
from app_modules.pdf_preflight import build_pdf_preflight_report


_READY_IMAGE_STATUS = {"required_destinations_ready": True}
_READY_OUTPUT = {"pictures_added": True, "day_images": {"Day 1": {"path": "/bank/oslo.jpg"}}}


def _state(warnings=()):
    return {
        "itinerary_html": "<html>ok</html>",
        "parsed_rows": [{"day": "Day 1", "type": "Arrival", "city": "Oslo"}],
        "output_edits": {**_READY_OUTPUT, "latest_client_output_warnings": list(warnings)},
    }


def test_review5_critical_client_warning_blocks_export():
    warning = {"code": "client_price_or_currency_leak", "severity": "critical", "message": "Client output includes price/currency text."}

    report = build_pdf_preflight_report(_state([warning]), _READY_IMAGE_STATUS)
    readiness = export_readiness_from_state(_state([warning]), _READY_IMAGE_STATUS)

    assert report.critical_count == 1
    assert report.can_export is False
    assert readiness.can_create_pdf is False
    assert readiness.client_risk_count == 1
    assert readiness.critical_issue_count == 1


def test_review5_review_warning_is_soft_gate():
    warning = {"code": "suspicious_am_pm_time_range", "severity": "review", "message": "Review suspicious time."}

    readiness = export_readiness_from_state(_state([warning]), _READY_IMAGE_STATUS)

    assert readiness.can_create_pdf is True
    assert readiness.review_issue_count == 1
    assert readiness.client_risk_count == 0
