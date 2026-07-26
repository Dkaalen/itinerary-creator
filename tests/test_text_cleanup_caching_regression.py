"""Correctness gates for precompiled and safely cached text cleanup."""

from __future__ import annotations

import re

import shared.source_text_cleanup as parser_cleanup
import place_alias_queries
import text_polish_modules.text_cleanup as polish_cleanup
from shared.text_cleanup_cache import clear_text_cleanup_caches, text_cleanup_cache_snapshot


def test_precompiled_case_replacements_preserve_legacy_order_and_flags() -> None:
    samples = (
        "south Coast whale Watching at HScandic Grand MArina",
        "standard doubel room near jokulsarlon glacier lagoon",
    )
    for sample in samples:
        expected = sample
        for pattern, replacement in (
            polish_cleanup.CASE_REPLACEMENTS + polish_cleanup.PROPER_NOUN_REPLACEMENTS
        ):
            expected = re.sub(pattern, replacement, expected, flags=re.IGNORECASE)
        assert polish_cleanup._apply_case_replacements(sample) == expected

    assert all(pattern.flags & re.IGNORECASE for pattern, _ in polish_cleanup.COMPILED_CASE_REPLACEMENTS)


def test_precompiled_common_replacements_keep_cached_and_uncached_output_identical() -> None:
    samples = (
        "Hlesinki: Private Trasnfer to Staion inclueded",
        "Reykjavik: South Coast if weather permits",
        "Rovaniemi: Husky rides (if snow)\nMeeting Point: Hotel Pickupo",
    )
    for sample in samples:
        assert parser_cleanup._fix_common_text_cached(sample) == parser_cleanup._fix_common_text_cached.__wrapped__(sample)

    assert all(pattern.flags & re.IGNORECASE for pattern, _ in parser_cleanup.COMPILED_COMMON_TEXT_REPLACEMENTS)


def test_cached_string_cores_match_uncached_implementations() -> None:
    sample = "Hlesinki and Reykajvik — south coast whale Watching"
    assert polish_cleanup._polish_text_fragment(sample) == polish_cleanup._polish_text_fragment.__wrapped__(sample)
    assert place_alias_queries._normalize_place_text_cached(sample) == place_alias_queries._normalize_place_text_cached.__wrapped__(sample)


def test_public_wrappers_remain_permissive_for_non_string_values() -> None:
    values = (["Hlesinki"], {"city": "Reykjavik"}, 1234, None)
    for value in values:
        assert parser_cleanup.fix_common_text(value) == parser_cleanup.fix_common_text(str(value or ""))
        assert place_alias_queries.normalize_place_text(value) == place_alias_queries.normalize_place_text(str(value or ""))
        expected_polished = "" if value is None else polish_cleanup.polish_client_text(str(value))
        assert polish_cleanup.polish_client_text(value) == expected_polished


def test_diagnostic_emitting_typo_check_is_not_cached(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(parser_cleanup.diagnostics, "warn", lambda *args, **kwargs: calls.append((args, kwargs)))

    parser_cleanup.check_for_unknown_typos("Brekafast")
    parser_cleanup.check_for_unknown_typos("Brekafast")

    assert len(calls) == 2
    assert not hasattr(parser_cleanup.check_for_unknown_typos, "cache_info")


def test_cleanup_caches_are_bounded_and_explicitly_clearable() -> None:
    clear_text_cleanup_caches()
    parser_cleanup.fix_common_text("Hlesinki private transfere")
    parser_cleanup.fix_common_text("Hlesinki private transfere")
    polish_cleanup.polish_client_text("south Coast whale Watching")
    polish_cleanup.polish_client_text("south Coast whale Watching")

    before = text_cleanup_cache_snapshot()
    assert all(info["maxsize"] == 8192 for info in before.values())
    assert before["fix_common_text"]["hits"] >= 1
    assert before["polish_text_fragment"]["hits"] >= 1

    clear_text_cleanup_caches()
    after = text_cleanup_cache_snapshot()
    assert all(info["currsize"] == 0 for info in after.values())
