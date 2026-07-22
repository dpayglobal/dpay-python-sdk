from __future__ import annotations

import pytest

from dpay import Currency, DPayValueError, Money


@pytest.mark.parametrize(
    ("minor", "expected"),
    [
        (1050, "10.50"),
        (1000, "10.00"),
        (5, "0.05"),
        (0, "0.00"),
        (-2000, "-20.00"),
        (-5, "-0.05"),
        (123456789, "1234567.89"),
    ],
)
def test_to_decimal_always_has_two_places(minor: int, expected: str) -> None:
    assert Money.pln(minor).to_decimal() == expected


def test_to_decimal_never_returns_negative_zero() -> None:
    assert Money.pln(0).to_decimal() == "0.00"


def test_pln_does_not_validate_amount() -> None:
    assert Money.pln(-1).minor == -1


def test_of_validates_currency() -> None:
    with pytest.raises(DPayValueError, match='Invalid currency code "pln"'):
        Money.of(100, "pln")


@pytest.mark.parametrize(
    ("decimal", "expected"),
    [("10", 1000), ("10.5", 1050), ("10.50", 1050), ("0.05", 5), ("-0.05", -5), ("0", 0)],
)
def test_from_decimal_right_pads_fraction(decimal: str, expected: int) -> None:
    assert Money.from_decimal(decimal, Currency.PLN).minor == expected


def test_from_decimal_rejects_garbage() -> None:
    with pytest.raises(DPayValueError, match='Invalid money amount "abc"'):
        Money.from_decimal("abc", Currency.PLN)


def test_from_decimal_rejects_three_decimal_places() -> None:
    with pytest.raises(DPayValueError):
        Money.from_decimal("10.123", Currency.PLN)


def test_from_decimal_validates_currency_before_amount() -> None:
    with pytest.raises(DPayValueError, match="Invalid currency code"):
        Money.from_decimal("abc", "pln")


def test_from_api_number_treats_int_as_major_units() -> None:
    assert Money.from_api_number(30, Currency.PLN).minor == 3000


def test_from_api_number_rounds_half_away_from_zero() -> None:
    assert Money.from_api_number(8.285, Currency.PLN).minor == 829


def test_from_api_number_rejects_bool() -> None:
    with pytest.raises(DPayValueError, match="Money value must be int, float or string"):
        Money.from_api_number(True, Currency.PLN)


def test_from_api_number_rejects_none() -> None:
    with pytest.raises(DPayValueError):
        Money.from_api_number(None, Currency.PLN)


def test_try_from_api_number_validates_currency_first() -> None:
    assert Money.try_from_api_number(10, "pln") is None


def test_try_from_api_number_never_raises() -> None:
    assert Money.try_from_api_number("abc", Currency.PLN) is None
    assert Money.try_from_api_number(True, Currency.PLN) is None
    assert Money.try_from_api_number(None, Currency.PLN) is None
    assert Money.try_from_api_number({}, Currency.PLN) is None


def test_equality_compares_amount_and_currency() -> None:
    assert Money.pln(100).equals(Money.pln(100))
    assert not Money.pln(100).equals(Money.of(100, Currency.EUR))
    assert Money.pln(100) == Money.pln(100)
    assert Money.pln(100) != Money.of(100, Currency.EUR)


def test_is_negative() -> None:
    assert Money.pln(-1).is_negative
    assert not Money.pln(0).is_negative


def test_money_is_hashable_and_frozen() -> None:
    assert len({Money.pln(1), Money.pln(1)}) == 1
    with pytest.raises(AttributeError):
        Money.pln(1).minor = 2  # type: ignore[misc]
