from __future__ import annotations

import pytest

from dpay._internal.php import (
    is_numeric,
    is_php_bool,
    is_php_float,
    is_php_int,
    is_scalar,
    php_int,
    php_json_encode,
    php_round,
    php_strval,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        (True, "1"),
        (False, ""),
        (42, "42"),
        (-7, "-7"),
        (10.0, "10"),
        (10.5, "10.5"),
        (0.1, "0.1"),
        (1 / 3, "0.33333333333333"),
        (1e25, "1.0E+25"),
        (-0.0, "-0"),
        (828.5, "828.5"),
        ("abc", "abc"),
    ],
)
def test_php_strval_matches_php_cast(value: object, expected: str) -> None:
    assert php_strval(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.5, 1), (1.5, 2), (2.5, 3), (-0.5, -1), (-1.5, -2), (828.5, 829), (0.4, 0), (-0.4, 0)],
)
def test_php_round_is_half_away_from_zero(value: float, expected: int) -> None:
    assert php_round(value) == expected


def test_python_round_would_diverge() -> None:
    assert round(828.5) == 828
    assert php_round(828.5) == 829


def test_bool_is_not_an_int_like_in_php() -> None:
    assert is_php_int(True) is False
    assert is_php_int(1) is True
    assert is_php_bool(True) is True
    assert is_php_float(1.0) is True
    assert is_php_float(1) is False


def test_is_scalar_matches_php() -> None:
    assert is_scalar("a") and is_scalar(1) and is_scalar(1.0) and is_scalar(True)
    assert not is_scalar(None)
    assert not is_scalar({})
    assert not is_scalar([])


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, True),
        (1.5, True),
        ("1", True),
        ("1.5", True),
        (" 2 ", True),
        ("abc", False),
        ("", False),
        (None, False),
    ],
)
def test_is_numeric(value: object, expected: bool) -> None:
    assert is_numeric(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("42", 42), ("42abc", 42), ("abc", 0), ("-7", -7), (True, 1), (None, 0), (3.9, 3)],
)
def test_php_int_never_raises(value: object, expected: int) -> None:
    assert php_int(value) == expected


def test_json_encode_uses_compact_separators() -> None:
    assert php_json_encode({"a": 1, "b": "x"}) == '{"a":1,"b":"x"}'


def test_json_encode_keeps_unicode_literal() -> None:
    assert php_json_encode({"a": "ĄŻ"}) == '{"a":"ĄŻ"}'


def test_json_encode_preserves_insertion_order() -> None:
    assert php_json_encode({"z": 1, "a": 2}) == '{"z":1,"a":2}'


def test_json_encode_leaves_slashes_by_default() -> None:
    assert php_json_encode({"u": "https://a/b"}) == '{"u":"https://a/b"}'


def test_json_encode_escapes_slashes_for_card_payload() -> None:
    assert php_json_encode({"DT": "12/25"}, escape_slashes=True) == '{"DT":"12\\/25"}'


def test_json_encode_renders_integral_floats_without_fraction() -> None:
    assert php_json_encode({"amount": 1.0}) == '{"amount":1}'
    assert php_json_encode({"amount": 29.99}) == '{"amount":29.99}'


def test_json_encode_empty_body_is_object() -> None:
    assert php_json_encode({}) == "{}"
