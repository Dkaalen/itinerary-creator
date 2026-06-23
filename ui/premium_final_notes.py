"""Premium final-page note rendering helpers."""

from __future__ import annotations

import re

from text_polish import polish_client_text
from ui.render_helpers import esc, normalize_list

_NOTE_RULES = [
    ("Hotel timings", re.compile(r"\b(hotel|check[- ]?in|check[- ]?out|accommodation)\b", re.I)),
    ("Extra nights", re.compile(r"\b(extra night|additional night|night can be added|budget)\b", re.I)),
    ("Optional transfers", re.compile(r"\b(private transfer|private transfers|railway station|bus terminal|airport|cruise port|optional add[- ]?on)\b", re.I)),
    ("Tailor-made additions", re.compile(r"\b(add more|additional activit|excursion|longer-duration|request|additional cost)\b", re.I)),
    ("Activity flexibility", re.compile(r"\b(activity|activities|weather|safety|availability)\b", re.I)),
    ("Transport schedules", re.compile(r"\b(transport|flight|flights|train|trains|bus|buses|ferr(?:y|ies)|cruise|cruises|schedule|timing|timings)\b", re.I)),
]


def premium_note_cards(paragraphs) -> list[tuple[str, str]]:
    """Return short titled note cards while preserving every note paragraph."""

    cards: list[tuple[str, str]] = []
    used_titles: set[str] = set()
    for paragraph in normalize_list(paragraphs):
        body = polish_client_text(paragraph)
        if not body:
            continue
        title = "Travel guidance"
        for candidate_title, pattern in _NOTE_RULES:
            if pattern.search(body):
                title = candidate_title
                break
        if title in used_titles:
            title = "Additional guidance"
        used_titles.add(title)
        cards.append((title, body))
    return cards


def render_premium_notes_inner_html(paragraphs) -> str:
    cards = premium_note_cards(paragraphs)
    if not cards:
        return ""
    html_text = '<div class="content-block notes-block premium-notes-grid">'
    for title, body in cards:
        html_text += '<div class="premium-note-card">'
        html_text += f'<div class="premium-note-card-title">{esc(title)}</div>'
        html_text += f'<div class="body-text note-paragraph">{esc(body)}</div>'
        html_text += '</div>'
    html_text += '</div>'
    return html_text
