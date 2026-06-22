"""Apply visual-editor summary payload fields."""


def apply_summary_payload(data, output_edits):
    summary = data.get("summary", {}) or {}
    if isinstance(summary.get("trip_glance"), dict):
        output_edits["trip_glance"] = {
            str(key).strip(): str(value).strip()
            for key, value in summary.get("trip_glance", {}).items()
            if str(key).strip()
        }
    if isinstance(summary.get("journey_arc"), list):
        output_edits["journey_arc"] = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in summary.get("journey_arc", [])
            if isinstance(row, dict)
        ]
