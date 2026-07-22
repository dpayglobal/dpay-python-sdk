from __future__ import annotations

from typing import Any

from dpay._internal.php import is_scalar, php_int
from dpay.currency import Currency
from dpay.money import Money


def _strict_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _money(raw: dict[str, Any], key: str) -> Money:
    return Money.try_from_api_number(raw.get(key, 0), Currency.PLN) or Money.pln(0)


def _flag(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    return php_int(value) == 1 if is_scalar(value) else False


class PayoutReceiver:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutReceiver:
        return cls(data)

    @property
    def nrb(self) -> str | None:
        return _strict_string(self.raw, "nrb")

    @property
    def title(self) -> str | None:
        return _strict_string(self.raw, "title")

    @property
    def amount(self) -> Money | None:
        return Money.try_from_api_number(self.raw.get("amount"), Currency.PLN)

    @property
    def service(self) -> str | None:
        return _strict_string(self.raw, "service")

    @property
    def receiver_name(self) -> str | None:
        return _strict_string(self.raw, "receiverName")

    @property
    def receiver_address(self) -> str | None:
        return _strict_string(self.raw, "receiverAddress")


class PayoutDetails:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.id = php_int(raw.get("id")) if is_scalar(raw.get("id")) else 0
        self.state = php_int(raw.get("state")) if is_scalar(raw.get("state")) else 0
        self.net = _money(raw, "net")
        self.fee = _money(raw, "fee")
        self.gross = _money(raw, "gross")
        self.creation_date = _strict_string(raw, "creation_date")
        self.is_direct_settlement = _flag(raw, "direct_settlement")
        self.nrb = _strict_string(raw, "nrb")
        self.is_declined = _flag(raw, "declined")
        self.decline_reason = _strict_string(raw, "decline_reason")
        self.decline_status = _strict_string(raw, "decline_status")
        receiver = raw.get("receiver")
        self.receiver = PayoutReceiver.from_api(receiver) if isinstance(receiver, dict) else None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutDetails:
        return cls(data)

    @property
    def is_waiting(self) -> bool:
        return self.state == 0

    @property
    def is_processed(self) -> bool:
        return self.state == 1

    @property
    def is_failed(self) -> bool:
        return self.state == -1
