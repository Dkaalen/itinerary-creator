"""Activity description helpers used by legacy UI rendering."""

from __future__ import annotations

import re

from itinerary_generation.activity_description_rules import keyword_activity_description, specific_activity_description
from itinerary_generation.activity_training_catalogue import catalogue_description_for_row
from itinerary_generation.product_rules import find_product_match
from itinerary_generation.render_text_helpers import get_detail_level_name
from itinerary_generation.titles import create_client_activity_title
from text_polish import polish_client_text, polish_title


_SUPPLIER_SECTION_LABEL_RE = re.compile(
    r"^\s*(?:overview|what(?:'|’)s included\??|what to expect\??|please note:?|not included:?|includes?:?|pick up\s*/\s*meeting point|meeting point)\s*$",
    flags=re.IGNORECASE,
)

_BAD_DESCRIPTION_FALLBACK_MARKERS = [
    "join a whale watching experience",
    "join a guided glacier experience",
    "enjoy a planned experience",
    "enjoy a guided experience",
    "enjoy this lagoon and wellness experience",
]


def _strip_supplier_day_heading(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = text.split("\n")
    if lines:
        lines[0] = re.sub(r"^\s*Day\s*\d+\s*[:\-–]\s*[^\n|]+\s*", "", lines[0], flags=re.IGNORECASE).strip()
    return "\n".join(line for line in lines if line.strip()).strip()


def _extract_section_after_label(text: str, labels: tuple[str, ...]) -> str:
    lines = [line.strip() for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    capture = False
    out: list[str] = []
    label_patterns = tuple(label.lower() for label in labels)
    for line in lines:
        clean = line.strip(" :-")
        lower = clean.lower()
        if not capture and any(lower.startswith(label) for label in label_patterns):
            capture = True
            remainder = re.sub(r"^\s*(?:" + "|".join(re.escape(label) for label in labels) + r")\s*[:?\-]*\s*", "", line, flags=re.IGNORECASE).strip()
            if remainder:
                out.append(remainder)
            continue
        if capture:
            if _SUPPLIER_SECTION_LABEL_RE.match(clean):
                break
            out.append(line)
    return "\n".join(out).strip()


def _trim_description_sentences(text: str, max_words: int = 90, min_sentences: int = 2) -> str:
    cleaned = polish_client_text(_strip_supplier_day_heading(text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|•")
    if not cleaned:
        return ""
    # Remove supplier sales closers that read poorly in a client proposal.
    cleaned = re.sub(r"\b(?:What are you waiting for\?|Start your adventure now by booking a date\.?|Come and join us[^.?!]*[.?!])", "", cleaned, flags=re.IGNORECASE).strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected: list[str] = []
    word_count = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = sentence.split()
        if selected and word_count + len(words) > max_words and len(selected) >= min_sentences:
            break
        selected.append(sentence)
        word_count += len(words)
        if word_count >= max_words and len(selected) >= min_sentences:
            break
    result = " ".join(selected).strip()
    if len(result.split()) < 12:
        return ""
    return result


def _real_supplier_description(row: dict, max_words: int = 90) -> str:
    """Prefer real supplier prose over generic fallbacks.

    This is intentionally broad and data-driven: if the row has a substantial
    day/activity body, use it before any keyword fallback such as whale/glacier.
    """
    raw_sources = [row.get("description", ""), row.get("details", ""), row.get("original_title", "")]
    for raw in raw_sources:
        text = str(raw or "")
        if not text.strip():
            continue
        # Prefer explicit narrative sections in supplier rows.
        for labels in (("What to expect", "What to expect?"), ("Overview",), ("Description",)):
            section = _extract_section_after_label(text, labels)
            candidate = _trim_description_sentences(section, max_words=max_words)
            if candidate:
                return candidate
        # Rows that only contain title/time/meeting/includes metadata do not
        # have narrative prose. Let the planned fallback write the description.
        if not re.match(r"^\s*Day\s*\d+\s*[:\-–]", text, flags=re.IGNORECASE):
            lower_text = text.lower()
            has_metadata = any(marker in lower_text for marker in [" time:", " meeting point", " includes:", " what's included", " what’s included"])
            pipe_parts = [part.strip() for part in re.split(r"\s*\|\s*", text) if part.strip()]
            has_pipe_metadata = len(pipe_parts) >= 3 and any(
                re.search(r"\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d+(?:\.\d+)?\s*(?:hrs?|hours?))\b", part, flags=re.IGNORECASE)
                for part in pipe_parts[1:]
            )
            has_section = any(marker in lower_text for marker in ["overview", "what to expect", "description:"])
            if (has_metadata or has_pipe_metadata) and not has_section:
                continue
        candidate = _trim_description_sentences(text, max_words=max_words)
        if candidate:
            return candidate
    return ""


def get_activity_description(row, detail_level=None):
    detail_level = detail_level or get_detail_level_name()
    title = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    city = str(row.get("city", "")).strip().lower()

    real_description = _real_supplier_description(
        row,
        max_words=115 if re.search(r"^\s*Day\s*\d+\s*:", str(row.get("details", "")), flags=re.IGNORECASE) else 85,
    )
    if real_description:
        return real_description

    product_match = find_product_match(row)
    if product_match and product_match.description:
        return product_match.description

    specific_description = specific_activity_description(title=title, city=city, detail_level=detail_level)
    if specific_description:
        return specific_description

    # The training catalogue is a structured example layer, not the highest
    # authority.  Use it after explicit supplier prose and specific product
    # templates, but before broad keyword fallbacks such as generic walking,
    # boat, Northern Lights, or planned-experience copy.
    catalogue_description = catalogue_description_for_row(row)
    if catalogue_description:
        return catalogue_description

    clean_title = polish_title(create_client_activity_title(row) or row.get("title", "") or "Included experience")
    city_name = polish_title(row.get("city", ""))
    destination_phrase = f" in {city_name}" if city_name else ""
    combined = f"{clean_title} {title}".lower()
    keyword_description = keyword_activity_description(combined=combined, destination_phrase=destination_phrase)
    if keyword_description:
        return keyword_description
    return f"Take part in the arranged activity{destination_phrase}, adding a clear highlight to the day without exposing raw supplier notes."


__all__ = [
    "_BAD_DESCRIPTION_FALLBACK_MARKERS",
    "_SUPPLIER_SECTION_LABEL_RE",
    "_extract_section_after_label",
    "_real_supplier_description",
    "_strip_supplier_day_heading",
    "_trim_description_sentences",
    "get_activity_description",
]
