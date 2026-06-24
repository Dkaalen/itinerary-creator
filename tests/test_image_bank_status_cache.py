from app_modules.image_bank_status_cache import (
    clear_image_bank_status_cache,
    get_cached_image_bank_status,
    image_request_signature,
    store_image_bank_status,
)


def test_image_request_signature_is_stable_for_equivalent_requests():
    first = [{"destination": "Oslo", "season": "Summer"}]
    second = [{"season": "Summer", "destination": "Oslo"}]

    assert image_request_signature(first) == image_request_signature(second)


def test_cached_image_bank_status_reuses_matching_signature():
    calls = []
    state = {}

    def status_func(requests):
        calls.append(list(requests or []))
        return {"required_destinations_ready": True, "count": len(calls)}

    requests = [{"destination": "Oslo"}]
    first = get_cached_image_bank_status(state, requests, status_func)
    second = get_cached_image_bank_status(state, list(requests), status_func)

    assert first == second == {"required_destinations_ready": True, "count": 1}
    assert len(calls) == 1


def test_cached_image_bank_status_invalidates_when_request_changes():
    calls = []
    state = {}

    def status_func(requests):
        calls.append(list(requests or []))
        return {"count": len(calls)}

    assert get_cached_image_bank_status(state, [{"destination": "Oslo"}], status_func)["count"] == 1
    assert get_cached_image_bank_status(state, [{"destination": "Bergen"}], status_func)["count"] == 2


def test_store_and_clear_image_bank_status_cache():
    state = {}
    requests = [{"destination": "Oslo"}]

    store_image_bank_status(state, requests, {"ready": True})
    assert get_cached_image_bank_status(state, requests, lambda _requests: {"ready": False}) == {"ready": True}

    clear_image_bank_status_cache(state)
    assert get_cached_image_bank_status(state, requests, lambda _requests: {"ready": False}) == {"ready": False}
