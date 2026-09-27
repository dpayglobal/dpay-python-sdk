from __future__ import annotations

import re
from typing import Any

from dpay._internal.php import is_scalar, php_strval
from dpay.currency import Currency
from dpay.money import Money
from dpay.payment.enums import TransactionStatus

_HTTP_URL = re.compile(r"^https?://")


def _string_or_empty(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    return php_strval(value) if is_scalar(value) else ""


def _string_or_none(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return php_strval(value) if is_scalar(value) else None


def _strict_string_or_none(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _money_or_zero(data: dict[str, Any], key: str) -> Money:
    return Money.try_from_api_number(data.get(key, 0), Currency.PLN) or Money.pln(0)


class RegisteredPayment:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.transaction_id = _string_or_empty(raw, "transactionId")
        self.message = _string_or_empty(raw, "msg")
        self.ipksef = _strict_string_or_none(raw, "ipksef")

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RegisteredPayment:
        return cls(data)

    @property
    def redirect_url(self) -> str | None:
        return self.message if _HTTP_URL.match(self.message) else None

    @property
    def is_paid(self) -> bool:
        return self.message == "Transaction paid"

    @property
    def is_internal_processing(self) -> bool:
        return self.message == "Internal processing"

    @property
    def card_recurring_alias(self) -> str | None:
        additional = self.raw.get("additionalInfo")
        if isinstance(additional, dict):
            return _strict_string_or_none(additional, "card_recurring_alias")
        return None

    @property
    def recurring_alias(self) -> str | None:
        """Alias of the recurring payment registered with this payment (``with_recurring_registration``)."""
        return _strict_string_or_none(self._recurring_registration(), "alias")

    @property
    def recurring_methods(self) -> list[str]:
        methods = self._recurring_registration().get("methods")
        if isinstance(methods, dict):
            methods = list(methods.values())
        if not isinstance(methods, list):
            return []
        return [method for method in methods if isinstance(method, str)]

    def _recurring_registration(self) -> dict[str, Any]:
        additional = self.raw.get("additionalInfo")
        registration = additional.get("recurring_registration") if isinstance(additional, dict) else None
        return registration if isinstance(registration, dict) else {}


class TransactionRefund:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.payment_id = _string_or_empty(raw, "payment_id")
        self.value = _money_or_zero(raw, "value")
        status = _string_or_none(raw, "status")
        self.status = status if status is not None else TransactionStatus.PAID
        self.creation_date = _string_or_none(raw, "creation_date")
        self.payment_date = _string_or_none(raw, "payment_date")

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TransactionRefund:
        return cls(data)


class Transaction:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        transaction = raw.get("transaction")
        transaction = transaction if isinstance(transaction, dict) else {}

        self.id = _string_or_empty(transaction, "id")
        self.value = _money_or_zero(transaction, "value")
        self.status = _string_or_empty(transaction, "status")
        self.payment_method = _string_or_none(transaction, "payment_method")
        self.creation_date = _string_or_none(transaction, "creation_date")
        self.payment_date = _strict_string_or_none(transaction, "payment_date")
        self.is_settled = bool(transaction.get("settled", False))
        self.is_refunded = bool(transaction.get("refunded", False))
        self.refunded_amount = _money_or_zero(transaction, "refunded_amount")
        self.available_refund_amount = _money_or_zero(transaction, "available_refund_amount")
        self.is_fully_refunded = bool(transaction.get("fully_refunded", False))
        self.is_direct = bool(transaction.get("direct", False))
        self.gateway_id = _strict_string_or_none(transaction, "gateway_id")

        payer = raw.get("payer")
        self.payer: dict[str, Any] = payer if isinstance(payer, dict) else {}

        refunds = raw.get("refunds")
        refunds = refunds if isinstance(refunds, list) else []
        self.refunds = [TransactionRefund.from_api(item) for item in refunds if isinstance(item, dict)]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Transaction:
        return cls(data)

    @property
    def is_paid(self) -> bool:
        return self.status in (TransactionStatus.PAID, TransactionStatus.CAPTURED)
