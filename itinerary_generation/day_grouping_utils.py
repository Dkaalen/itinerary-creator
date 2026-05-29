"""Small day-number helper shared by grouping modules."""

from __future__ import annotations


def get_day_number(day_text):
    digits = "".join(character for character in str(day_text) if character.isdigit())

    if digits:
        return int(digits)

    return 0
