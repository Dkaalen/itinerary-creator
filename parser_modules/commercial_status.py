"""Commercial-status helpers for parsed itinerary rows.

The parser should classify rows as included by default. Optional/self-arranged
state is commercial metadata, separate from operational type detection, and must
not leak across rows.
"""

OPTIONAL = "optional"
INCLUDED = "included"
SELF_ARRANGED = "self_arranged"
EXCLUDED = "excluded"

REASON_EXPLICIT_OPTIONAL = "explicit_optional"
REASON_OPTIONAL_TEXT_PREFIX = "optional_text_prefix"
REASON_DEFAULT_INCLUDED = "default_included"
REASON_SELF_TRANSFER = "self_transfer"
REASON_COST_NOT_INCLUDED = "cost_not_included"
REASON_NOT_INCLUDED_MARKER = "not_included_marker"


SELF_ARRANGED_MARKERS = [
    "self arranged",
    "self arrnaged",
    "self arrange",
    "cost not included",
    "cost not inclueded",
    "price not included",
    "flight cost not",
]


def normalize_commercial_text(*values):
    """Return compact lower-case text for commercial-status matching."""
    text = " ".join(str(value or "") for value in values).lower().replace("-", " ")
    return " ".join(text.replace(",", " ").split())


def initial_commercial_state(is_optional):
    """Return the row's initial commercial state before title/detail parsing."""
    if is_optional:
        return OPTIONAL, REASON_EXPLICIT_OPTIONAL
    return INCLUDED, REASON_DEFAULT_INCLUDED


def infer_commercial_status(is_optional, item_type, title, details):
    """Classify the row's commercial status from structured parser fields."""
    text = normalize_commercial_text(item_type, title, details)
    if is_optional:
        return OPTIONAL, REASON_EXPLICIT_OPTIONAL
    if "self transfer" in text:
        return SELF_ARRANGED, REASON_SELF_TRANSFER
    if any(marker in text for marker in SELF_ARRANGED_MARKERS):
        return SELF_ARRANGED, REASON_COST_NOT_INCLUDED
    # Rental-car rows often include both the included rental package and a
    # small excluded commercial note such as "Not included: safety deposit".
    # The vehicle itself must stay included; exclusions can surface the deposit
    # as a specific cost note without moving the whole row out of the itinerary.
    if "not included" in text and "rental" in text and "deposit" in text:
        return INCLUDED, REASON_DEFAULT_INCLUDED
    if "not included" in text and str(item_type or "").lower() not in {"activity", "hotel"}:
        return EXCLUDED, REASON_NOT_INCLUDED_MARKER
    return INCLUDED, REASON_DEFAULT_INCLUDED


def infer_optional_row_type(description):
    """Infer the operational type for rows pasted with row type Optional.

    Explicit Optional rows are usually optional experiences. Do not let included
    phrases such as "transfer to/from the harbour" inside an activity's
    inclusion list turn the row into transport. Only the leading title segment
    may change the underlying type.
    """
    text = str(description or "").lower()
    leading = text.split(" - ", 1)[0].split(" | ", 1)[0]
    if any(marker in leading for marker in ["hotel", "accommodation", "check in"]):
        return "Hotel"
    if "flight" in leading:
        return "Flight"
    if "train" in leading:
        return "Train"
    if "cruise" in leading:
        return "Cruise"
    if "ferry" in leading:
        return "Ferry"
    if any(marker in leading for marker in ["transfer", "coach", "bus", "airport"]):
        return "Transfer"
    return "Activity"


def mark_optional_row(row, reason=REASON_OPTIONAL_TEXT_PREFIX):
    """Mutate and return a parsed row dict as optional in one place."""
    row["is_optional"] = True
    row["commercial_status"] = OPTIONAL
    row["commercial_reason"] = reason
    row_id = str(row.get("row_id") or "")
    if row_id and not row_id.startswith("opt_"):
        row["row_id"] = f"opt_{row_id}"
    return row
