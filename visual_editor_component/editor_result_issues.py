"""Apply visual-editor issue flag payload fields."""


def apply_issue_flags_payload(data, output_edits):
    if not isinstance(data.get("issue_flags"), list):
        return
    cleaned_flags = []
    for flag in data.get("issue_flags") or []:
        if not isinstance(flag, dict):
            continue
        key = str(flag.get("key", "")).strip()
        corrected = str(flag.get("corrected", "")).strip()
        if not key and not corrected:
            continue
        cleaned_flags.append({
            "key": key,
            "label": str(flag.get("label", "")).strip(),
            "original": str(flag.get("original", "")).strip(),
            "corrected": corrected,
        })
    if cleaned_flags:
        existing = output_edits.get("visual_editor_issue_flags") if isinstance(output_edits.get("visual_editor_issue_flags"), list) else []
        seen = {(str(item.get("key", "")), str(item.get("corrected", ""))) for item in existing if isinstance(item, dict)}
        for flag in cleaned_flags:
            dedupe_key = (flag["key"], flag["corrected"])
            if dedupe_key not in seen:
                existing.append(flag)
                seen.add(dedupe_key)
        output_edits["visual_editor_issue_flags"] = existing
