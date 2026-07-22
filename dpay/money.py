from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from dpay._internal.php import is_php_float, is_php_int, php_round
from dpay.currency import Currency
from dpay.exceptions import DPayValueError

_DECIMAL = re.compile(r"^(-?)(\d+)(?:\.(\d{1,2}))?$")


@dataclass(frozen=True)
class Money:
    minor: int
    currency: str

    @classmethod
    def pln(cls, minor: int) -> Money:
        return cls(minor, Currency.PLN)

    @classmethod
    def of(cls, minor: int, currency: str) -> Money:
        Currency.assert_valid(currency)
        return cls(minor, currency)

    @classmethod
    def from_decimal(cls, decimal: str, currency: str) -> Money:
        Currency.assert_valid(currency)
        parsed = _parse_decimal(decimal)
        if parsed is None:
            raise DPayValueError(f'Invalid money amount "{decimal}"')
        return cls(parsed, currency)

    @classmethod
    def from_api_number(cls, value: Any, currency: str) -> Money:
        if is_php_int(value):
            return cls.of(value * 100, currency)
        if is_php_float(value):
            return cls.of(php_round(value * 100), currency)
        if isinstance(value, str):
            return cls.from_decimal(value, currency)
        raise DPayValueError("Money value must be int, float or string")

    @classmethod
    def try_from_api_number(cls, value: Any, currency: str) -> Money | None:
        if not Currency.is_valid(currency):
            return None
        if is_php_int(value):
            return cls(value * 100, currency)
        if is_php_float(value):
            return cls(php_round(value * 100), currency)
        if isinstance(value, str):
            parsed = _parse_decimal(value)
            return None if parsed is None else cls(parsed, currency)
        return None

    def to_decimal(self) -> str:
        absolute = abs(self.minor)
        sign = "-" if self.minor < 0 else ""
        return f"{sign}{absolute // 100}.{absolute % 100:02d}"

    @property
    def is_negative(self) -> bool:
        return self.minor < 0

    def equals(self, other: Money) -> bool:
        return self.minor == other.minor and self.currency == other.currency

    def __str__(self) -> str:
        return f"{self.to_decimal()} {self.currency}"


def _parse_decimal(decimal: str) -> int | None:
    match = _DECIMAL.match(decimal)
    if match is None:
        return None
    fraction = (match.group(3) or "").ljust(2, "0")
    minor = int(match.group(2)) * 100 + int(fraction)
    return -minor if match.group(1) == "-" else minor
