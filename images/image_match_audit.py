"""Audit day image selections against day context.

These helpers are intentionally presentation-free. They let the staged editor
and PDF export warn about image drift without changing the client-facing layout.
"""

from __future__ import annotations

from dataclasses import dataclass

import diagnostics
from pathlib import Path

from images.fallback import is_global_default_candidate
from images.day_image_selection import normalize_day_image_match, normalize_day_image_matches
from images.image_bank import image_bank_status_for_paths
from images.image_overrides import normalize_image_mode
from images.matcher_context import build_day_context
from images.matcher_scoring import (
    candidate_destination_matches,
    is_protected_specialty_image_allowed,
    score_image_for_day,
)
from images.metadata import ImageCandidate, extract_image_metadata, infer_seasons, infer_themes, tokenize
from images.scanner import ImageBankIndex, coerce_image_bank_paths, get_image_bank_index


@dataclass(frozen=True)
class ImageAuditWarning:
    code: str
    message: str
    severity: str = "warning"
    day: str = ""
    path: str = ""


def _normalize_path_key(path) -> str:
    try:
        return str(Path(path).expanduser().resolve()).lower().replace("\\", "/")
    except (OSError, TypeError, ValueError) as error:
        diagnostics.warn_exception("image_match_audit", "Could not normalize image path for audit.", error, str(path or ""), source="images.image_match_audit")
        return str(path or "").lower().replace("\\", "/")


def _match_path(match: dict | None) -> str:
    return str((match or {}).get("path", "") or "").strip()


def _candidate_lookup(candidates: list[ImageCandidate]) -> dict[str, ImageCandidate]:
    lookup: dict[str, ImageCandidate] = {}
    for candidate in candidates:
        lookup[_normalize_path_key(candidate.path)] = candidate
    return lookup


def _fallback_candidate_from_path(path_text: str, image_bank_scan_paths) -> ImageCandidate | None:
    """Build lightweight metadata for a selected image outside the scanned bank."""

    if not path_text:
        return None
    path = Path(path_text)
    try:
        resolved = path.resolve()
    except OSError as error:
        diagnostics.warn_exception("image_match_audit", "Could not resolve selected image path for audit.", error, path_text, source="images.image_match_audit")
        resolved = path

    for base in coerce_image_bank_paths(image_bank_scan_paths):
        try:
            if resolved.exists() and resolved.is_relative_to(base.resolve()):
                return extract_image_metadata(resolved, base)
        except (OSError, TypeError, ValueError) as error:
            diagnostics.warn_exception("image_match_audit", "Could not compare selected image with scan path.", error, str(base), source="images.image_match_audit")
            continue

    if not resolved.exists():
        return None

    city = resolved.parent.name or ""
    filename = resolved.stem
    token_source = " ".join([city, filename.replace("_", " ")])
    tokens = tokenize(token_source)
    return ImageCandidate(
        path=str(resolved),
        country="",
        city=city,
        filename=filename,
        tokens=tuple(sorted(tokens)),
        themes=tuple(sorted(infer_themes(tokens))),
        seasons=tuple(sorted(infer_seasons(tokens))),
    )


def _candidate_for_match(
    match: dict | None,
    candidates: list[ImageCandidate],
    image_bank_scan_paths,
    candidate_lookup: dict[str, ImageCandidate] | None = None,
) -> ImageCandidate | None:
    path_text = _match_path(match)
    if not path_text:
        return None
    lookup = candidate_lookup if candidate_lookup is not None else _candidate_lookup(candidates)
    candidate = lookup.get(_normalize_path_key(path_text))
    if candidate:
        return candidate
    return _fallback_candidate_from_path(path_text, image_bank_scan_paths)


def _choice_mode(output_edits: dict | None, day: str) -> str:
    try:
        choice = ((output_edits or {}).get("day_images", {}) or {}).get(day, {})
    except AttributeError:
        choice = {}
    if not isinstance(choice, dict):
        choice = {}
    return normalize_image_mode(
        choice.get("mode", "auto"),
        removed=choice.get("removed", False),
        path=choice.get("path", ""),
    )


def _format_name(path_text: str) -> str:
    try:
        return Path(path_text).name
    except (OSError, TypeError, ValueError):
        return str(path_text or "selected image")


def _default_images_allowed_for_final(output_edits: dict | None) -> bool:
    return not bool((output_edits or {}).get("block_default_final_images"))


def audit_day_image_match(
    day: str,
    rows: list[dict],
    match: dict | None,
    *,
    output_edits: dict | None = None,
    image_bank_scan_paths="image_bank",
    image_bank_index: ImageBankIndex | None = None,
    candidate_lookup: dict[str, ImageCandidate] | None = None,
) -> tuple[ImageAuditWarning, ...]:
    """Return warnings for one day image selection.

    The audit is deliberately non-invasive: it does not choose another image.
    It only catches cases where a manual/automatic choice looks unsupported by
    the day context, especially narrow specialty images and wrong-destination
    manual selections.
    """

    mode = _choice_mode(output_edits, day)
    if mode == "none":
        return ()

    match = normalize_day_image_match(day, match)
    path_text = _match_path(match)
    if not path_text:
        return ()

    index = image_bank_index or get_image_bank_index(image_bank_scan_paths)
    candidates = list(index.candidates)
    candidate = _candidate_for_match(match, candidates, image_bank_scan_paths, candidate_lookup)
    if not candidate:
        if mode == "manual":
            return (
                ImageAuditWarning(
                    code="manual_image_not_found_for_audit",
                    message=f"Manual picture for {day} could not be found for image-context audit.",
                    severity="warning",
                    day=day,
                    path=path_text,
                ),
            )
        return ()

    context = build_day_context(day, rows or [])
    warnings: list[ImageAuditWarning] = []
    display_name = _format_name(path_text)

    allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, context)
    if not allowed:
        warnings.append(ImageAuditWarning(
            code="image_protected_specialty_mismatch",
            message=(
                f"{day} uses {display_name}, but this protected specialty image is not supported "
                f"by the day text: {blocked_reason}."
            ),
            severity="error",
            day=day,
            path=path_text,
        ))
        return tuple(warnings)

    if is_global_default_candidate(candidate) and not _default_images_allowed_for_final(output_edits):
        warnings.append(ImageAuditWarning(
            code="default_image_selected_for_final_output",
            message=(
                f"{day} uses {display_name}, which is a bundled Default fallback. "
                "It can be used for export when no better destination image is selected."
            ),
            severity="info",
            day=day,
            path=path_text,
        ))

    score, reasons = score_image_for_day(candidate, context)
    reason_text = "; ".join(reasons or [])
    destination_match = candidate_destination_matches(candidate, context) or is_global_default_candidate(candidate)

    if mode == "manual" and not destination_match:
        warnings.append(ImageAuditWarning(
            code="manual_image_destination_mismatch",
            message=(
                f"Manual picture for {day} comes from {candidate.city or 'an unknown folder'}; "
                "it does not clearly match the day destination."
            ),
            severity="warning",
            day=day,
            path=path_text,
        ))

    conflict = "conflict:" in reason_text.lower()
    if mode == "manual" and (score <= 0 or conflict):
        warnings.append(ImageAuditWarning(
            code="manual_image_context_mismatch",
            message=(
                f"Manual picture for {day} has weak support from the day text. "
                f"Audit reason: {reason_text or 'no matching image context'}"
            ),
            severity="warning",
            day=day,
            path=path_text,
        ))
    elif mode == "auto" and score > 0 and score < 18 and is_global_default_candidate(candidate):
        warnings.append(ImageAuditWarning(
            code="automatic_image_low_confidence",
            message=(
                f"Automatic picture for {day} is a low-confidence default fallback. "
                "Review it in Picture review before export."
            ),
            severity="info",
            day=day,
            path=path_text,
        ))

    return tuple(warnings)


def audit_day_image_matches(
    grouped_days: dict,
    image_matches: dict,
    *,
    output_edits: dict | None = None,
    image_bank_scan_paths="image_bank",
) -> tuple[ImageAuditWarning, ...]:
    warnings: list[ImageAuditWarning] = []
    index = get_image_bank_index(image_bank_scan_paths)
    status = image_bank_status_for_paths(image_bank_scan_paths)
    candidate_lookup = _candidate_lookup(list(index.candidates))
    image_matches = normalize_day_image_matches(image_matches, image_bank_status=status)
    if grouped_days and status.get("missing_full_bank"):
        warnings.append(ImageAuditWarning(
            code="image_bank_full_missing",
            message=str(status.get("blocking_message") or "Full destination image bank is missing; bundled fallback images may be used until the destination bank is connected."),
            severity="warning",
            day="",
            path="",
        ))

    for day, rows in (grouped_days or {}).items():
        warnings.extend(audit_day_image_match(
            day,
            list(rows or []),
            (image_matches or {}).get(day),
            output_edits=output_edits,
            image_bank_scan_paths=image_bank_scan_paths,
            image_bank_index=index,
            candidate_lookup=candidate_lookup,
        ))
    return tuple(warnings)
