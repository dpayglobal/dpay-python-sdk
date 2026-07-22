from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dpay.exceptions import DPayValueError
from dpay.money import Money
from dpay.payment.enums import PayoutFeeMode


class PayoutPosition:
    def __init__(self, iban: str, title: str, amount: Money) -> None:
        if iban == "":
            raise DPayValueError("Payout IBAN must not be empty")
        if title == "" or len(title) > 255:
            raise DPayValueError("Payout title must be 1-255 characters")
        self.iban = iban
        self.title = title
        self.amount = amount

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
