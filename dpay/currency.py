from __future__ import annotations

import re

from dpay.exceptions import DPayValueError

_PATTERN = re.compile(r"^[A-Z]{3}$")


class Currency:
    PLN = "PLN"
    EUR = "EUR"
    CZK = "CZK"

    def __init__(self) -> None:
        raise DPayValueError("Currency is not instantiable")

    @staticmethod
    def is_valid(currency: str) -> bool:
        return _PATTERN.match(currency) is not None

    @staticmethod
    def assert_valid(currency: str) -> None:
        if not Currency.is_valid(currency):
            raise DPayValueError(f'Invalid currency code "{currency}"')
