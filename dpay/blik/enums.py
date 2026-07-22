from __future__ import annotations

from typing import Literal

from dpay.exceptions import DPayValueError

BlikAliasTypeValue = Literal["UID", "PAYID"]


class BlikAliasType:
    UID = "UID"
    PAYID = "PAYID"

    ALL = (UID, PAYID)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in BlikAliasType.ALL:
            raise DPayValueError(f'Invalid BLIK alias type "{value}"')
