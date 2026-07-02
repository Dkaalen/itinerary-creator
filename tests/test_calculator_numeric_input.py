from calculator.numeric_input import optional_numeric_input, parse_numeric_input


def test_parse_numeric_input_supports_spreadsheet_arithmetic() -> None:
    assert parse_numeric_input("100/10*0.8") == 8
    assert parse_numeric_input("=100 * (1 - 20%)") == 80
    assert parse_numeric_input("2,5*4") == 10


def test_parse_numeric_input_rejects_unsafe_or_invalid_input() -> None:
    assert parse_numeric_input("SUM(1,2)") == 0
    assert parse_numeric_input("__import__('os')") == 0
    assert parse_numeric_input("100/0") == 0


def test_optional_numeric_input_preserves_blank_values() -> None:
    assert optional_numeric_input("") is None
    assert optional_numeric_input("None") is None
    assert optional_numeric_input("=10/2") == 5
