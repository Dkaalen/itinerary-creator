def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label}\nExpected: {expected!r}\nActual:   {actual!r}"
        )


def assert_contains(text, expected, label):
    if expected not in text:
        raise AssertionError(
            f"{label}\nExpected to find: {expected!r}\nActual text: {text!r}"
        )
