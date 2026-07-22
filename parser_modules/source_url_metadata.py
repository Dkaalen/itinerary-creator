"""Keep source URLs as parser metadata rather than client-facing text."""

from __future__ import annotations

from dataclasses import dataclass

from shared.url_metadata import extract_url_metadata


@dataclass(frozen=True)
class ParsedSourceText:
    raw_line: str
    description: str
    urls: tuple[str, ...]


def parse_source_url_metadata(raw_line: object, description: object) -> ParsedSourceText:
    """Return URL-free parser text and stable source URL metadata."""

    raw = extract_url_metadata(raw_line)
    details = extract_url_metadata(description)
    urls = tuple(dict.fromkeys((*details.urls, *raw.urls)))
    return ParsedSourceText(raw_line=raw.text, description=details.text, urls=urls)


def attach_source_url_metadata(row: dict, urls: tuple[str, ...]) -> dict:
    """Attach source URL metadata without changing row identity."""

    clean_urls = tuple(str(url).strip() for url in urls if str(url).strip())
    row["source_url"] = clean_urls[0] if clean_urls else ""
    row["source_urls"] = list(clean_urls)
    return row


__all__ = ["ParsedSourceText", "attach_source_url_metadata", "parse_source_url_metadata"]
