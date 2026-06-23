"""Ownership helpers for generated itinerary copy and editor HTML.

Generated preview defaults should be refreshable when the generator changes.
Only explicit user edits should become persistent manual overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup

INTRO_GENERATOR_VERSION = "destination-copy-profiles1"
BLOCKS_GENERATOR_VERSION = "blocks-ownership-v1"

_INTRO_MANUAL_KEY = "intro_manual_override"
_INTRO_GENERATED_KEY = "intro_generated_value"
_INTRO_VERSION_KEY = "intro_generator_version"
_INTRO_SIGNATURE_KEY = "intro_source_signature"

_BLOCKS_MANUAL_KEY = "blocks_manual_override"
_BLOCKS_GENERATED_KEY = "blocks_html_generated_value"
_BLOCKS_VERSION_KEY = "blocks_html_generator_version"

_GENERATED_INTRO_RE = re.compile(
    r"(?:"
    r"\bThe journey continues\b|"
    r"\bContinue your Norway in a Nutshell journey\b|"
    r"\bTravel (?:from|to|towards)\b|"
    r"\bSail from\b|"
    r"\bToday you explore\b|"
    r"\bThe day centres on\b|"
    r"\bBegin with Oslo from the water\b|"
    r"\bis the main arranged experience\b|"
    r"\bAfter check-out\b|"
    r"\bYour journey comes to a close\b|"
    r"\bWelcome to\b"
    r")",
    flags=re.IGNORECASE,
)


def _as_text(value: Any) -> str:
    return str(value) if value is not None else ""


def normalize_copy_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _as_text(value)).strip()


def _norm_for_compare(value: Any) -> str:
    return normalize_copy_text(value).casefold()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def day_source_signature(rows: Sequence[Mapping[str, Any]] | None) -> str:
    """Return a stable signature for facts that should affect generated day copy."""

    serializable: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        serializable.append(
            {
                "day": row.get("day", ""),
                "type": row.get("effective_type") or row.get("type", ""),
                "city": row.get("city", ""),
                "title": row.get("title", ""),
                "original_title": row.get("original_title", ""),
                "details": row.get("details", ""),
                "time": row.get("time", ""),
                "duration": row.get("duration", ""),
                "meeting_point": row.get("meeting_point", ""),
                "end_point": row.get("end_point", ""),
                "includes": row.get("includes", []),
            }
        )
    payload = json.dumps(serializable, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def looks_generated_intro(value: Any) -> bool:
    text = normalize_copy_text(value)
    return bool(text and _GENERATED_INTRO_RE.search(text))


@dataclass(frozen=True)
class ResolvedIntro:
    intro: str
    manual_override: bool
    generated_value: str
    generator_version: str
    source_signature: str

    def metadata(self) -> dict[str, Any]:
        return {
            _INTRO_GENERATED_KEY: self.generated_value,
            _INTRO_VERSION_KEY: self.generator_version,
            _INTRO_SIGNATURE_KEY: self.source_signature,
            _INTRO_MANUAL_KEY: self.manual_override,
        }


def _candidate_from(owner: Mapping[str, Any] | None) -> tuple[bool, str, bool | None, str, str, str]:
    if not isinstance(owner, Mapping) or "intro" not in owner:
        return False, "", None, "", "", ""
    manual = _bool(owner.get(_INTRO_MANUAL_KEY)) if _INTRO_MANUAL_KEY in owner else None
    return (
        True,
        normalize_copy_text(owner.get("intro", "")),
        manual,
        normalize_copy_text(owner.get(_INTRO_GENERATED_KEY, "")),
        _as_text(owner.get(_INTRO_VERSION_KEY, "")),
        _as_text(owner.get(_INTRO_SIGNATURE_KEY, "")),
    )


def resolve_intro(
    *,
    day_edits: Mapping[str, Any] | None,
    typed_day: Mapping[str, Any] | None,
    generated_intro: str,
    source_signature: str,
) -> ResolvedIntro:
    """Resolve visible intro while separating generated defaults from manual edits."""

    generated_intro = normalize_copy_text(generated_intro)
    for owner in (typed_day, day_edits):
        present, value, manual, stored_generated, stored_version, stored_signature = _candidate_from(owner)
        if not present:
            continue
        if manual is True:
            return ResolvedIntro(value, True, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if not value:
            continue
        # Explicit generated metadata means the value is refreshable unless the
        # editor has marked it as manual.
        if manual is False:
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if stored_generated and _norm_for_compare(value) == _norm_for_compare(stored_generated):
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if stored_version and stored_version != INTRO_GENERATOR_VERSION:
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if stored_signature and stored_signature != source_signature:
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if _norm_for_compare(value) == _norm_for_compare(generated_intro):
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        if looks_generated_intro(value):
            return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)
        return ResolvedIntro(value, True, generated_intro, INTRO_GENERATOR_VERSION, source_signature)

    return ResolvedIntro(generated_intro, False, generated_intro, INTRO_GENERATOR_VERSION, source_signature)


def apply_intro_metadata(day_edits: dict[str, Any], resolved: ResolvedIntro) -> None:
    if not isinstance(day_edits, dict):
        return
    day_edits["intro"] = resolved.intro
    day_edits.update(resolved.metadata())


def html_text(value: Any) -> str:
    html = _as_text(value)
    if not html:
        return ""
    return normalize_copy_text(BeautifulSoup(html, "html.parser").get_text(" "))


def html_equivalent(left: Any, right: Any) -> bool:
    return html_text(left).casefold() == html_text(right).casefold()


def _blocks_owner(owner: Mapping[str, Any] | None) -> tuple[bool, str, bool | None, str]:
    if not isinstance(owner, Mapping):
        return False, "", None, ""
    if "blocks_html" in owner:
        html = _as_text(owner.get("blocks_html", ""))
    else:
        blocks = owner.get("blocks")
        if not isinstance(blocks, (list, tuple)) or not blocks:
            return False, "", None, ""
        first = blocks[0]
        if not isinstance(first, Mapping):
            return False, "", None, ""
        html = _as_text(first.get("content_html", first.get("html", "")))
    manual = _bool(owner.get(_BLOCKS_MANUAL_KEY)) if _BLOCKS_MANUAL_KEY in owner else None
    generated = _as_text(owner.get(_BLOCKS_GENERATED_KEY, ""))
    return True, html, manual, generated


@dataclass(frozen=True)
class ResolvedBlocksHtml:
    html: str
    manual_override: bool
    generated_value: str

    def metadata(self) -> dict[str, Any]:
        return {
            _BLOCKS_GENERATED_KEY: self.generated_value,
            _BLOCKS_VERSION_KEY: BLOCKS_GENERATOR_VERSION,
            _BLOCKS_MANUAL_KEY: self.manual_override,
        }


def resolve_blocks_html(
    *,
    day_edits: Mapping[str, Any] | None,
    typed_day: Mapping[str, Any] | None,
    generated_blocks_html: str,
) -> ResolvedBlocksHtml:
    """Resolve body HTML ownership for preview/PDF fallback decisions."""

    generated_blocks_html = _as_text(generated_blocks_html)
    for owner in (typed_day, day_edits):
        present, html, manual, stored_generated = _blocks_owner(owner)
        if not present:
            continue
        # Empty body with an explicit blocks_html key is an intentional manual clear.
        if html == "" and (manual is True or (isinstance(owner, Mapping) and "blocks_html" in owner)):
            return ResolvedBlocksHtml("", True, generated_blocks_html)
        if manual is True:
            return ResolvedBlocksHtml(html, True, generated_blocks_html)
        if manual is False:
            return ResolvedBlocksHtml(generated_blocks_html, False, generated_blocks_html)
        if stored_generated and html_equivalent(html, stored_generated):
            return ResolvedBlocksHtml(generated_blocks_html, False, generated_blocks_html)
        if html_equivalent(html, generated_blocks_html):
            return ResolvedBlocksHtml(generated_blocks_html, False, generated_blocks_html)
        # Legacy non-empty body HTML without ownership is treated as manual for
        # backward compatibility. New generated editor commits carry
        # blocks_manual_override=false, so those do not force fallback.
        return ResolvedBlocksHtml(html, True, generated_blocks_html)
    return ResolvedBlocksHtml(generated_blocks_html, False, generated_blocks_html)


def blocks_html_is_manual(owner: Mapping[str, Any] | None) -> bool:
    if not isinstance(owner, Mapping):
        return False
    if _BLOCKS_MANUAL_KEY in owner:
        return _bool(owner.get(_BLOCKS_MANUAL_KEY))
    # Pre-ownership saved day body HTML is assumed to be manual to avoid data
    # loss. Generated editor saves now mark false explicitly.
    if "blocks_html" in owner:
        return True
    blocks = owner.get("blocks")
    return isinstance(blocks, (list, tuple)) and bool(blocks)
