from __future__ import annotations

from typing import Literal

from dpay.exceptions import DPayValueError

TransactionTypeValue = Literal[
    "transfers",
    "dcb_gateway",
    "card_auth",
    "mb_way_direct",
    "card_recurring",
]

TransactionStatusValue = Literal["paid", "created", "processing", "expired", "captured"]

PayoutFeeModeValue = Literal["net", "gross"]


class TransactionType:
    TRANSFERS = "transfers"
    DCB_GATEWAY = "dcb_gateway"
    CARD_AUTH = "card_auth"
    MB_WAY_DIRECT = "mb_way_direct"
    CARD_RECURRING = "card_recurring"

    ALL = (
        TRANSFERS,
        DCB_GATEWAY,
        CARD_AUTH,
        MB_WAY_DIRECT,
        CARD_RECURRING,
    )

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in TransactionType.ALL:
            raise DPayValueError(f'Invalid transaction type "{value}"')


class TransactionStatus:
    PAID = "paid"
    CREATED = "created"
    PROCESSING = "processing"
    EXPIRED = "expired"
    CAPTURED = "captured"

    ALL = (PAID, CREATED, PROCESSING, EXPIRED, CAPTURED)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in TransactionStatus.ALL:
            raise DPayValueError(f'Invalid transaction status "{value}"')


class PayoutFeeMode:
    NET = "net"
    GROSS = "gross"

    ALL = (NET, GROSS)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in PayoutFeeMode.ALL:
            raise DPayValueError(f'Invalid payout fee mode "{value}"')
