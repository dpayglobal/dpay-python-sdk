from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from dpay.exceptions import DPayValueError
from dpay.money import Money
from dpay.payment.enums import PayoutFeeMode

_WHITESPACE = re.compile(r"\s", re.ASCII)
_POLISH_IBAN = re.compile(r"PL[0-9]{26}")


class PayoutPosition:
    def __init__(self, iban: str, title: str, amount: Money) -> None:
        """``iban`` - Polish IBAN of one of your verified bank accounts (``PL`` + 26 digits, spaces allowed),
        sent as given; ``amount`` above 0."""
        if not PayoutPosition.is_valid_polish_iban(iban):
            raise DPayValueError(f'Payout IBAN "{iban}" must be a valid Polish IBAN (PL + 26 digits)')
        if title == "" or len(title) > 255:
            raise DPayValueError("Payout title must be 1-255 characters")
        if amount.minor <= 0:
            raise DPayValueError("Payout amount must be above 0")
        self.iban = iban
        self.title = title
        self.amount = amount

    @staticmethod
    def is_valid_polish_iban(iban: str) -> bool:
        """``PL`` + 26 digits after removing whitespace and upper-casing, with a valid ISO 13616 check
        (mod 97 = 1)."""
        normalized = _WHITESPACE.sub("", iban)
        normalized = "".join(char.upper() if "a" <= char <= "z" else char for char in normalized)
        if _POLISH_IBAN.fullmatch(normalized) is None:
            return False
        # Country code and check digits go to the end, letters become numbers (P = 25, L = 21)
        numeric = normalized[4:] + "2521" + normalized[2:4]
        return int(numeric) % 97 == 1

    def to_api(self) -> dict[str, Any]:
        return {
            "iban": self.iban,
            "title": self.title,
            "amount": float(self.amount.to_decimal()),
        }


class PayoutInstruction:
    def __init__(self, positions: Sequence[Any], fee_mode: str = PayoutFeeMode.NET) -> None:
        if len(positions) == 0:
            raise DPayValueError("Payout instruction requires at least one position")
        for position in positions:
            if not isinstance(position, PayoutPosition):
                raise DPayValueError("Positions must be PayoutPosition instances")
        PayoutFeeMode.assert_valid(fee_mode)
        self.positions: list[PayoutPosition] = list(positions)
        self.fee_mode = fee_mode

    @classmethod
    def create(cls, positions: Sequence[Any], fee_mode: str = PayoutFeeMode.NET) -> PayoutInstruction:
        return cls(positions, fee_mode)

    def to_api(self) -> dict[str, Any]:
        return {
            "fee_mode": self.fee_mode,
            "positions": [position.to_api() for position in self.positions],
        }
