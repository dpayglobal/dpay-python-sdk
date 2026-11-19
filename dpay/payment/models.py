from __future__ import annotations

import re
from typing import Any

from dpay._internal.php import is_php_float, is_php_int, is_scalar, php_strval
from dpay.currency import Currency
from dpay.money import Money
from dpay.payment.enums import TransactionStatus

_HTTP_URL = re.compile(r"^https?://")
# PHP preg_match('/^-?\d+$/') - ``$`` also matches before a final newline
_INTEGER_STRING = re.compile(r"^-?\d+$", re.ASCII)


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


def _string_or_int(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str):
        return value
    return str(value) if is_php_int(value) else None


def _valid_currency(currency: str) -> str:
    return currency if Currency.is_valid(currency) else Currency.PLN


class MultibancoReference:
    """Multibanco payment reference returned by the registration (``multibanco``).

    The payer pays it at an ATM or in online banking with the entity and reference numbers, so you can
    show them without redirecting to the gateway.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> MultibancoReference:
        return cls(data)

    @property
    def entity(self) -> str:
        """Entity number (5 digits)."""
        return _string_or_int(self.raw, "entity") or ""

    @property
    def reference(self) -> str:
        """Reference number (9 digits, without spaces)."""
        return _string_or_int(self.raw, "reference") or ""

    @property
    def amount(self) -> Money | None:
        """Amount to pay in ``currency`` (EUR)."""
        return Money.try_from_api_number(self.raw.get("amount"), self.currency)

    @property
    def currency(self) -> str:
        currency = _string_or_int(self.raw, "currency")
        return currency if currency is not None and Currency.is_valid(currency) else Currency.EUR

    @property
    def expires_at(self) -> str | None:
        """Expiry in UTC, ISO 8601 (e.g. ``2026-11-21T10:00:00+00:00``)."""
        return _string_or_int(self.raw, "expires_at")


class RegisteredTransaction:
    """The transaction of a registration answered "Transaction paid" (``additionalInfo.transaction``).

    The payment was already paid (e.g. a repeated registration). Its statuses differ from
    ``Transaction.status``: pending, paid, captured, canceled.
    """

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CAPTURED = "captured"
    STATUS_CANCELED = "canceled"

    def __init__(self, raw: dict[str, Any], currency: str = Currency.PLN) -> None:
        self.raw = raw
        # Currency of the registered amount - the object carries none.
        self.currency = _valid_currency(currency)

    @classmethod
    def from_api(cls, data: dict[str, Any], currency: str = Currency.PLN) -> RegisteredTransaction:
        return cls(data, currency)

    @property
    def payment_id(self) -> str:
        return _string_or_int(self.raw, "payment_id") or ""

    @property
    def status(self) -> str | None:
        return _string_or_int(self.raw, "status")

    @property
    def is_paid(self) -> bool:
        return self.status in (RegisteredTransaction.STATUS_PAID, RegisteredTransaction.STATUS_CAPTURED)

    @property
    def value(self) -> Money | None:
        return Money.try_from_api_number(self.raw.get("value"), self.currency)

    @property
    def email(self) -> str | None:
        return _string_or_int(self.raw, "email")

    @property
    def description(self) -> str | None:
        return _string_or_int(self.raw, "description")

    @property
    def name(self) -> str | None:
        return _string_or_int(self.raw, "name")

    @property
    def surname(self) -> str | None:
        return _string_or_int(self.raw, "surname")

    @property
    def pid(self) -> str | None:
        """Provider transaction identifier, when known."""
        return _string_or_int(self.raw, "pid")

    @property
    def mtid(self) -> str | None:
        return _string_or_int(self.raw, "mtid")

    @property
    def creation_date(self) -> str | None:
        return _string_or_int(self.raw, "creation_date")

    @property
    def payment_date(self) -> str | None:
        return _string_or_int(self.raw, "payment_date")


class TransactionUrls:
    """Return and IPN addresses stored with a transaction (``transaction.urls`` of ``payments.details()``)."""

    def __init__(self, success: str | None, fail: str | None, ipn: str | None) -> None:
        self.success = success
        self.fail = fail
        # ``None`` when the payment was registered without an IPN address.
        self.ipn = ipn

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TransactionUrls:
        return cls(
            _non_empty_string(data, "success"),
            _non_empty_string(data, "fail"),
            _non_empty_string(data, "ipn"),
        )


def _non_empty_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value != "" else None


class RegisteredPayment:
    def __init__(self, raw: dict[str, Any], currency: str = Currency.PLN) -> None:
        self.raw = raw
        # Currency of the registered amount (for ``paid_transaction``).
        self.currency = _valid_currency(currency)
        self.transaction_id = _string_or_empty(raw, "transactionId")
        self.message = _string_or_empty(raw, "msg")
        self.ipksef = _strict_string_or_none(raw, "ipksef")

    @classmethod
    def from_api(cls, data: dict[str, Any], currency: str = Currency.PLN) -> RegisteredPayment:
        return cls(data, currency)

    @property
    def multibanco(self) -> MultibancoReference | None:
        """Multibanco reference to show the payer (registration with the Multibanco channel)."""
        multibanco = self.raw.get("multibanco")
        return MultibancoReference.from_api(multibanco) if isinstance(multibanco, dict) else None

    @property
    def paid_transaction(self) -> RegisteredTransaction | None:
        """The already paid transaction of a "Transaction paid" answer (``additionalInfo.transaction``)."""
        additional = self.raw.get("additionalInfo")
        transaction = additional.get("transaction") if isinstance(additional, dict) else None
        return (
            RegisteredTransaction.from_api(transaction, self.currency)
            if isinstance(transaction, dict)
            else None
        )

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

    def _transaction(self) -> dict[str, Any]:
        transaction = self.raw.get("transaction")
        return transaction if isinstance(transaction, dict) else {}

    def _int_field(self, key: str) -> int | None:
        value = self._transaction().get(key)
        if isinstance(value, int) and is_php_int(value):
            return value
        if isinstance(value, str) and _INTEGER_STRING.match(value) is not None:
            return int(value)
        return None

    @property
    def rate(self) -> str | None:
        """dpay commission rate in percent as sent (e.g. ``1.50``)."""
        value = self._transaction().get("rate")
        if isinstance(value, str) or is_php_int(value) or is_php_float(value):
            return php_strval(value)
        return None

    @property
    def minimal_fee(self) -> int | None:
        """Minimal commission as sent by the API (``minimal_fee``, e.g. 20 = 0.20 PLN)."""
        return self._int_field("minimal_fee")

    @property
    def permanent_fee(self) -> int | None:
        """Added fixed commission as sent by the API (``permanent_fee``, cards only)."""
        return self._int_field("permanent_fee")

    @property
    def urls(self) -> TransactionUrls | None:
        """Return and IPN addresses of the registration."""
        urls = self._transaction().get("urls")
        return TransactionUrls.from_api(urls) if isinstance(urls, dict) else None
