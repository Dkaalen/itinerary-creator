"""Safe spreadsheet-style numeric input parsing for calculator values."""

from __future__ import annotations

import ast
from decimal import Decimal, DecimalException
import operator
import re
from typing import Any

_BLANK_MARKERS = {"", "none", "nan", "null"}
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_PERCENT_RE = re.compile(r"(?P<number>(?:\d+(?:\.\d*)?|\.\d+))\s*%")
_ALLOWED_CHARS_RE = re.compile(r"^[0-9+\-*/().\s%]+$")


def parse_numeric_input(value: Any, *, default: float = 0.0) -> float:
    """Return a float from a number or simple Excel-style arithmetic input.

    Supported examples: ``100``, ``=100/10*0.8``, ``100 * (1 - 20%)``.
    Names, functions, cell references, and other Python/JS syntax are rejected.
    """

    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = _normalise_expression_text(value)
    if text.casefold() in _BLANK_MARKERS or not text:
        return default
    if not _ALLOWED_CHARS_RE.fullmatch(text):
        return default
    try:
        parsed = ast.parse(text, mode="eval")
        result = _eval_node(parsed.body)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError):
        return default
    return float(result)


def parse_decimal_input(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    """Return an exact finite Decimal from spreadsheet-style arithmetic input."""

    if value in (None, ""):
        return default
    if isinstance(value, Decimal):
        return value if value.is_finite() else default
    if isinstance(value, (int, float)):
        try:
            result = Decimal(str(value))
        except (DecimalException, ValueError):
            return default
        return result if result.is_finite() else default
    text = _normalise_expression_text(value)
    if text.casefold() in _BLANK_MARKERS or not text:
        return default
    if not _ALLOWED_CHARS_RE.fullmatch(text):
        return default
    try:
        parsed = ast.parse(text, mode="eval")
        result = _eval_decimal_node(parsed.body)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError, DecimalException):
        return default
    return result if result.is_finite() else default


def optional_numeric_input(value: Any) -> float | None:
    """Return None for blank markers, otherwise parse spreadsheet-style input."""

    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.casefold() in _BLANK_MARKERS:
        return None
    return parse_numeric_input(value)


def _normalise_expression_text(value: Any) -> str:
    text = str(value).strip().replace(",", ".")
    if text.startswith("="):
        text = text[1:].strip()
    text = _PERCENT_RE.sub(r"(\g<number>/100)", text)
    return text


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return float(_OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return float(_UNARY_OPERATORS[type(node.op)](_eval_node(node.operand)))
    raise ValueError(f"Unsupported numeric expression: {ast.dump(node)}")


def _eval_decimal_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left = _eval_decimal_node(node.left)
        right = _eval_decimal_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ZeroDivisionError
        return left / right
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        value = _eval_decimal_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError(f"Unsupported numeric expression: {ast.dump(node)}")
