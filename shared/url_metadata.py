"""Extract source URLs without allowing them into client-facing prose.

URLs are metadata.  Parser, identity and rendering code should use these helpers
instead of treating a URL or URL slug as supplier-owned copy evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_VALID_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_LABELLED_DAMAGED_URL_RE = re.compile(
    r"(?:\s*[-–—|·]\s*)?\bURL\s*:\s*https?\s*:\s*/\s*/[^\n|]*(?=$|\n)",
    re.IGNORECASE,
)
_EMPTY_URL_LABEL_RE = re.compile(r"(?:\s*[-–—|·]\s*)?\bURL\s*:\s*(?=$|\n)", re.IGNORECASE)
_REPEATED_SEPARATORS_RE = re.compile(r"\s+(?:[-–—|·]\s*){2,}")


@dataclass(frozen=True)
class UrlExtraction:
    """URL metadata separated from cleaned source text."""

    text: str
    urls: tuple[str, ...]

    @property
    def primary_url(self) -> str:
        return self.urls[0] if self.urls else ""


def extract_url_metadata(value: object) -> UrlExtraction:
    """Return URL-free text and stable, de-duplicated valid URLs.

    Normal URLs are retained as metadata.  Previously damaged labelled URL
    tails such as ``URL: https: //example. com/...`` cannot be reconstructed
    safely, so they are removed from prose without inventing a URL.
    """

    text = str(value or "").replace("\xa0", " ")
    urls: list[str] = []

    def _capture(match: re.Match[str]) -> str:
        url = match.group(0).rstrip(".,;:!?)]}")
        if url and url not in urls:
            urls.append(url)
        suffix = match.group(0)[len(url) :]
        return suffix

    text = _VALID_URL_RE.sub(_capture, text)
    text = _LABELLED_DAMAGED_URL_RE.sub("", text)
    text = _EMPTY_URL_LABEL_RE.sub("", text)
    text = _REPEATED_SEPARATORS_RE.sub(" - ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines()).strip()
    return UrlExtraction(text=text, urls=tuple(urls))


def strip_urls(value: object) -> str:
    """Return client-safe text with URLs and labelled URL tails removed."""

    return extract_url_metadata(value).text


__all__ = ["UrlExtraction", "extract_url_metadata", "strip_urls"]
