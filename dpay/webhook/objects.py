"""Typed ``data.object`` models of webhook events. Amounts in minor units, times in UTC (ISO 8601)."""

from __future__ import annotations

from typing import Any

from dpay._internal.php import is_php_int
from dpay.currency import Currency
from dpay.money import Money
from dpay.webhook.failure import Failure


def _string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str):
        return value
    return str(value) if is_php_int(value) else None


def _int_or_none(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    return value if is_php_int(value) else None


def _dict_or_none(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = data.get(key)
    return value if isinstance(value, dict) else None


def _currency(data: dict[str, Any]) -> str:
    """``currency`` of the object, PLN when missing or invalid."""
    currency = data.get("currency")
    return currency if isinstance(currency, str) and Currency.is_valid(currency) else Currency.PLN


def _money(data: dict[str, Any], key: str, currency: str) -> Money:
    """Amount in minor units (an integer in the payload); 0 when missing."""
    minor = data.get(key)
    return Money.of(minor if isinstance(minor, int) and is_php_int(minor) else 0, currency)


def _failure(data: dict[str, Any]) -> Failure | None:
    failure = _dict_or_none(data, "failure")
    return None if failure is None else Failure.from_api(failure)


class PaymentObject:
    """The ``payment`` object of payment.* events. Amounts in minor units of ``currency``."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_CAPTURED = "captured"
    STATUS_FAILED = "failed"
    STATUS_REVERSED = "reversed"
    STATUS_CHARGED_BACK = "charged_back"

    SEQUENCE_FIRST = "first"
    SEQUENCE_SUBSEQUENT = "subsequent"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PaymentObject:
        return cls(data)

    @property
    def id(self) -> str:
        """Payment ID - the transactionId of the registration."""
        return _string(self.raw, "id") or ""

    @property
    def status(self) -> str | None:
        return _string(self.raw, "status")

    @property
    def currency(self) -> str:
        return _currency(self.raw)

    @property
    def amount(self) -> Money:
        return _money(self.raw, "amount", self.currency)

    @property
    def amount_refunded(self) -> Money:
        return _money(self.raw, "amount_refunded", self.currency)

    @property
    def amount_captured(self) -> Money:
        """Total captured from a card pre-authorisation."""
        return _money(self.raw, "amount_captured", self.currency)

    @property
    def description(self) -> str | None:
        return _string(self.raw, "description")

    @property
    def created(self) -> str | None:
        return _string(self.raw, "created")

    @property
    def paid_at(self) -> str | None:
        """``None`` until the payment is paid."""
        return _string(self.raw, "paid_at")

    @property
    def payment_method(self) -> dict[str, Any] | None:
        """``{type, <type>: {details}}``, e.g. ``{"type": "blik", "blik": {"flow": "code"}}``.

        ``None`` while unknown.
        """
        return _dict_or_none(self.raw, "payment_method")

    @property
    def payment_method_type(self) -> str | None:
        """blik, card, bank_transfer, twisto, multibanco, blik_pay_later, mb_way, paypal, paypo or paysafecard
        (``payment_method.type``)."""
        return _string(self.payment_method or {}, "type")

    @property
    def failure(self) -> Failure | None:
        """Decline reason in payment.failed."""
        return _failure(self.raw)

    @property
    def is_recurring(self) -> bool:
        return _dict_or_none(self.raw, "recurring") is not None

    @property
    def recurring_alias(self) -> str | None:
        """Alias of the recurring payment (BLIK or card) this payment belongs to."""
        return _string(_dict_or_none(self.raw, "recurring") or {}, "alias")

    @property
    def recurring_registration(self) -> str | None:
        """ID of the payment that registered the recurring payment."""
        return _string(_dict_or_none(self.raw, "recurring") or {}, "registration")

    @property
    def recurring_sequence(self) -> str | None:
        """``first`` (the registration payment) or ``subsequent`` (a charge)."""
        return _string(_dict_or_none(self.raw, "recurring") or {}, "sequence")

    @property
    def merchant_reference(self) -> str | None:
        """Your ``reference`` from the registration."""
        return _string(_dict_or_none(self.raw, "references") or {}, "merchant")

    @property
    def provider_reference(self) -> str | None:
        """Transaction ID at the provider (BLIK, card processor), if available."""
        return _string(_dict_or_none(self.raw, "references") or {}, "provider")

    @property
    def custom(self) -> str | None:
        return _string(self.raw, "custom")


class RefundObject:
    """The ``refund`` object of refund.* events."""

    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RefundObject:
        return cls(data)

    @property
    def id(self) -> str | None:
        """Refund ID (``ZWROT-...``); ``None`` for a refund rejected before it was created."""
        return _string(self.raw, "id")

    @property
    def payment(self) -> str | None:
        """ID of the refunded payment."""
        return _string(self.raw, "payment")

    @property
    def status(self) -> str | None:
        return _string(self.raw, "status")

    @property
    def currency(self) -> str:
        return _currency(self.raw)

    @property
    def amount(self) -> Money:
        return _money(self.raw, "amount", self.currency)

    @property
    def created(self) -> str | None:
        return _string(self.raw, "created")

    @property
    def succeeded_at(self) -> str | None:
        return _string(self.raw, "succeeded_at")

    @property
    def failure(self) -> Failure | None:
        """Rejection reason in refund.failed, e.g. ``refund_window_expired``."""
        return _failure(self.raw)


class RecurringPaymentObject:
    """The ``recurring_payment`` object of recurring_payment.* events.

    Identified by the registration payment.
    """

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_DECLINED = "declined"

    CANCELED_BY_MERCHANT = "merchant"
    CANCELED_BY_CUSTOMER = "customer"
    CANCELED_BY_DPAY = "dpay"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecurringPaymentObject:
        return cls(data)

    def _terms(self) -> dict[str, Any]:
        return _dict_or_none(self.raw, "terms") or {}

    @property
    def id(self) -> str:
        """ID of the registration payment."""
        return _string(self.raw, "id") or ""

    @property
    def alias(self) -> str | None:
        """The alias you charge the recurring payment with."""
        return _string(self.raw, "alias")

    @property
    def status(self) -> str | None:
        return _string(self.raw, "status")

    @property
    def canceled_by(self) -> str | None:
        """merchant, customer or dpay when canceled; ``None`` in other states."""
        return _string(self.raw, "canceled_by")

    @property
    def payment_method(self) -> dict[str, Any] | None:
        return _dict_or_none(self.raw, "payment_method")

    @property
    def payment_method_type(self) -> str | None:
        return _string(self.payment_method or {}, "type")

    @property
    def model(self) -> str | None:
        """Recurring model: A, M or O (BLIK)."""
        return _string(self._terms(), "model")

    @property
    def frequency(self) -> str | None:
        """e.g. ``1M``."""
        return _string(self._terms(), "frequency")

    @property
    def limit_amount(self) -> int | None:
        """Single charge limit in minor units."""
        return _int_or_none(self._terms(), "limit_amount")

    @property
    def total_limit_amount(self) -> int | None:
        """Total limit in minor units."""
        return _int_or_none(self._terms(), "total_limit_amount")

    @property
    def starts_on(self) -> str | None:
        """YYYY-MM-DD."""
        return _string(self._terms(), "starts_on")

    @property
    def expires_on(self) -> str | None:
        """YYYY-MM-DD."""
        return _string(self._terms(), "expires_on")

    @property
    def created(self) -> str | None:
        return _string(self.raw, "created")


class PayoutObject:
    """The ``payout`` object of payout.* events (account events, without a service)."""

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PayoutObject:
        return cls(data)

    @property
    def id(self) -> str:
        """Payout ID - the ``withdraw_id`` of ``payouts.details()``."""
        return _string(self.raw, "id") or ""

    @property
    def status(self) -> str | None:
        return _string(self.raw, "status")

    @property
    def currency(self) -> str:
        return _currency(self.raw)

    @property
    def amount(self) -> Money:
        """Net payout amount."""
        return _money(self.raw, "amount", self.currency)

    @property
    def fee(self) -> Money:
        return _money(self.raw, "fee", self.currency)

    @property
    def bank_account_last4(self) -> str | None:
        """Last 4 digits of the destination account."""
        return _string(_dict_or_none(self.raw, "bank_account") or {}, "last4")

    @property
    def created(self) -> str | None:
        return _string(self.raw, "created")

    @property
    def paid_at(self) -> str | None:
        return _string(self.raw, "paid_at")

    @property
    def failure(self) -> Failure | None:
        """In payout.failed: ``payout_failed``, ``provider_code`` tells what happened to the funds."""
        return _failure(self.raw)
