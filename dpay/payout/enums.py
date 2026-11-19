from __future__ import annotations

from typing import Any, Literal

from dpay._internal.php import is_php_int
from dpay.exceptions import DPayValueError

PayoutTypeValue = Literal["standard", "direct", "paysafecard"]


class PayoutState:
    """Payout ``state``: 0 waiting, 1 processed, -1 failure."""

    WAITING = 0
    PROCESSED = 1
    FAILED = -1

    ALL = (WAITING, PROCESSED, FAILED)

    @staticmethod
    def assert_valid(value: Any) -> None:
        if not is_php_int(value) or value not in PayoutState.ALL:
            raise DPayValueError(f'Invalid payout state "{value}"')


class PayoutType:
    """Payout ``type`` in the payout list: ``direct`` covers exactly one payment (1:1 payout instruction,
    refund form payout)."""

    STANDARD = "standard"
    DIRECT = "direct"
    PAYSAFECARD = "paysafecard"

    ALL = (STANDARD, DIRECT, PAYSAFECARD)

    @staticmethod
    def assert_valid(value: Any) -> None:
        if not isinstance(value, str) or value not in PayoutType.ALL:
            raise DPayValueError(f'Invalid payout type "{value}"')
