from __future__ import annotations

from typing import Literal

from dpay.exceptions import DPayValueError

BlikAliasTypeValue = Literal["UID"]


class BlikAliasType:
    # BLIK OneClick alias. Recurring payments (PAYID) are handled by ``DPayClient.recurring``.
    UID = "UID"

    ALL = (UID,)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in BlikAliasType.ALL:
            raise DPayValueError(f'Invalid BLIK alias type "{value}"')
