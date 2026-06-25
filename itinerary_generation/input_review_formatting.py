"""Format structured input review summaries for debug/reporting surfaces."""

from __future__ import annotations

from itinerary_generation.input_review_models import StructuredInputReview


def format_structured_input_review(review: StructuredInputReview) -> str:
    counts = ", ".join(f"{label}: {count}" for label, count in review.service_counts.items()) or "none"
    lines = [
        "Structured Input Review",
        f"Status: {review.status_label}",
        f"Rows: {review.row_count}",
        f"Days: {review.day_count}",
        f"Route: {review.route_text}",
        f"Services: {counts}",
        f"Parser confidence: {review.average_confidence}%",
        f"Rows needing review: {review.low_confidence_count}",
        f"Suggested fixes: {review.suggested_fix_count}",
        f"Acceptable parser fixes: {len(review.correction_actions)}",
        f"Issues: {review.critical_issue_count} critical / {review.review_issue_count} review / {review.issue_count} total",
    ]
    if review.review_flags:
        flags = ", ".join(f"{label}: {count}" for label, count in review.review_flags.items())
        lines.append(f"Review flags: {flags}")
    blockers = [row for row in review.row_reviews if row.review_priority == "Blocker"]
    needs_review = [row for row in review.row_reviews if row.review_priority == "Review"]
    if review.correction_actions:
        lines.append("Safe parser fixes ready")
        for action in review.correction_actions[:5]:
            lines.append(f"- Row {action.row_number}: {action.action_label}")
    if blockers:
        lines.append("Correction queue: blockers first")
        for row in blockers[:5]:
            lines.append(f"- Row {row.row_number} [{row.next_action}] {row.day} · {row.service_type}: {row.primary_fix}")
    if needs_review:
        lines.append("Review queue: confirm before polishing")
        for row in needs_review[:5]:
            lines.append(f"- Row {row.row_number} [{row.next_action}] {row.day} · {row.service_type}: {row.primary_fix}")
    for issue in review.issues[:12]:
        prefix = f"{issue.day}: " if issue.day else ""
        lines.append(f"- [{issue.severity}] {prefix}{issue.message}")
    return "\n".join(lines)
