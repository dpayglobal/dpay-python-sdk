"""Typed ``data.object`` models of webhook events and decline codes (SDK 0.3.0)."""

from __future__ import annotations

from typing import Any

from dpay import (
    DeclineCode,
    FailureCategory,
    Money,
    PaymentObject,
    PayoutObject,
    RecurringPaymentObject,
    RefundObject,
    WebhookEvent,
)


def _event(type_: str, item: dict[str, Any]) -> WebhookEvent:
    return WebhookEvent.from_api(
        {
            "id": "evt_01k6a8q2m4pz7h8c3v5n9t2x6y",
            "type": type_,
            "api_version": "2026-10-01",
            "created": "2026-09-27T10:05:00Z",
            "livemode": True,
            "service": "abc123",
            "data": {"object": item},
        }
    )


def test_payment_succeeded() -> None:
    event = _event(
        "payment.succeeded",
        {
            "object": "payment",
            "id": "8F2A11C4-5B6D-4E7F-8A9B-0C1D2E3F4A5B",
            "status": "succeeded",
            "amount": 14900,
            "currency": "PLN",
            "amount_refunded": 0,
            "amount_captured": 0,
            "description": "Order 2026/09/123",
            "created": "2026-09-27T10:03:12Z",
            "paid_at": "2026-09-27T10:05:00Z",
            "payment_method": {"type": "blik", "blik": {"flow": "code"}},
            "failure": None,
            "recurring": None,
            "references": {"merchant": "2026/09/123", "provider": "1234567890"},
            "custom": "order-789",
        },
    )

    payment = event.payment
    assert payment is not None
    assert event.refund is None
    assert event.recurring_payment is None
    assert event.payout is None
    assert payment.id == "8F2A11C4-5B6D-4E7F-8A9B-0C1D2E3F4A5B"
    assert payment.status == PaymentObject.STATUS_SUCCEEDED
    assert payment.amount == Money.pln(14900)
    assert payment.amount_refunded == Money.pln(0)
    assert payment.amount_captured.minor == 0
    assert payment.description == "Order 2026/09/123"
    assert payment.created == "2026-09-27T10:03:12Z"
    assert payment.paid_at == "2026-09-27T10:05:00Z"
    assert payment.payment_method_type == "blik"
    assert payment.payment_method == {"type": "blik", "blik": {"flow": "code"}}
    assert payment.failure is None
    assert not payment.is_recurring
    assert payment.recurring_alias is None
    assert payment.merchant_reference == "2026/09/123"
    assert payment.provider_reference == "1234567890"
    assert payment.custom == "order-789"
    assert payment.raw is event.object


def test_payment_failed_recurring_charge_in_euro() -> None:
    payment = _event(
        "payment.failed",
        {
            "object": "payment",
            "id": "P-2",
            "status": "failed",
            "amount": 4999,
            "currency": "EUR",
            "amount_refunded": 0,
            "amount_captured": 0,
            "description": None,
            "created": "2026-10-01T08:00:00Z",
            "paid_at": None,
            "payment_method": None,
            "failure": {
                "code": "insufficient_funds",
                "message": "Insufficient funds",
                "category": "customer",
                "retryable": True,
                "provider_code": "INSUFFICIENT_FUNDS",
            },
            "recurring": {"alias": "SUB-0001", "registration": "P-1", "sequence": "subsequent"},
            "references": {"merchant": None, "provider": None},
            "custom": None,
        },
    ).payment

    assert payment is not None
    assert payment.status == PaymentObject.STATUS_FAILED
    assert payment.amount == Money.of(4999, "EUR")
    assert payment.paid_at is None
    assert payment.payment_method_type is None
    assert payment.merchant_reference is None
    assert payment.is_recurring
    assert payment.recurring_alias == "SUB-0001"
    assert payment.recurring_registration == "P-1"
    assert payment.recurring_sequence == PaymentObject.SEQUENCE_SUBSEQUENT
    failure = payment.failure
    assert failure is not None
    assert failure.code == DeclineCode.INSUFFICIENT_FUNDS
    assert failure.message == "Insufficient funds"
    assert failure.category == FailureCategory.CUSTOMER
    assert failure.is_retryable
    assert failure.provider_code == "INSUFFICIENT_FUNDS"


def test_refund_failed() -> None:
    refund = _event(
        "refund.failed",
        {
            "object": "refund",
            "id": None,
            "payment": "8F2A11C4-5B6D-4E7F-8A9B-0C1D2E3F4A5B",
            "status": "failed",
            "amount": 2000,
            "currency": "PLN",
            "created": "2026-10-01T08:00:00Z",
            "succeeded_at": None,
            "failure": {
                "code": "refund_window_expired",
                "message": "The refund period has expired",
                "category": "merchant",
                "retryable": False,
                "provider_code": None,
            },
        },
    ).refund

    assert refund is not None
    assert refund.id is None
    assert refund.payment == "8F2A11C4-5B6D-4E7F-8A9B-0C1D2E3F4A5B"
    assert refund.status == RefundObject.STATUS_FAILED
    assert refund.amount.minor == 2000
    assert refund.succeeded_at is None
    failure = refund.failure
    assert failure is not None
    assert failure.code == DeclineCode.REFUND_WINDOW_EXPIRED
    assert failure.category == FailureCategory.MERCHANT
    assert not failure.is_retryable
    assert failure.provider_code is None


def test_recurring_payment_canceled() -> None:
    recurring = _event(
        "recurring_payment.canceled",
        {
            "object": "recurring_payment",
            "id": "P-1",
            "alias": "SUB-0001",
            "status": "canceled",
            "canceled_by": "customer",
            "payment_method": {"type": "blik", "blik": {"flow": "recurring"}},
            "terms": {
                "model": "A",
                "frequency": "1M",
                "limit_amount": 5999,
                "total_limit_amount": 71988,
                "starts_on": "2026-11-01",
                "expires_on": "2027-09-30",
            },
            "created": "2026-09-26T10:00:00Z",
        },
    ).recurring_payment

    assert recurring is not None
    assert recurring.id == "P-1"
    assert recurring.alias == "SUB-0001"
    assert recurring.status == RecurringPaymentObject.STATUS_CANCELED
    assert recurring.canceled_by == RecurringPaymentObject.CANCELED_BY_CUSTOMER
    assert recurring.payment_method_type == "blik"
    assert recurring.model == "A"
    assert recurring.frequency == "1M"
    assert recurring.limit_amount == 5999
    assert recurring.total_limit_amount == 71988
    assert recurring.starts_on == "2026-11-01"
    assert recurring.expires_on == "2027-09-30"
    assert recurring.created == "2026-09-26T10:00:00Z"


def test_recurring_payment_model_o_has_no_limits() -> None:
    recurring = _event(
        "recurring_payment.activated",
        {
            "object": "recurring_payment",
            "id": "P-1",
            "alias": "SUB-0002",
            "status": "active",
            "canceled_by": None,
            "payment_method": None,
            "terms": {
                "model": "O",
                "frequency": None,
                "limit_amount": None,
                "total_limit_amount": "100",
                "starts_on": None,
                "expires_on": None,
            },
            "created": "2026-09-26T10:00:00Z",
        },
    ).recurring_payment

    assert recurring is not None
    assert recurring.status == RecurringPaymentObject.STATUS_ACTIVE
    assert recurring.canceled_by is None
    assert recurring.limit_amount is None
    # Only JSON integers are limits
    assert recurring.total_limit_amount is None
    assert recurring.frequency is None


def test_payout_failed() -> None:
    payout = _event(
        "payout.failed",
        {
            "object": "payout",
            "id": "12345",
            "status": "failed",
            "amount": 2715,
            "fee": 306,
            "currency": "PLN",
            "bank_account": {"last4": "2874"},
            "created": "2026-08-01T08:00:00Z",
            "paid_at": None,
            "failure": {
                "code": "payout_failed",
                "message": "The payout could not be completed",
                "category": "merchant",
                "retryable": False,
                "provider_code": "RETURNED",
            },
        },
    ).payout

    assert payout is not None
    assert payout.id == "12345"
    assert payout.status == PayoutObject.STATUS_FAILED
    assert payout.amount.minor == 2715
    assert payout.fee.minor == 306
    assert payout.bank_account_last4 == "2874"
    assert payout.paid_at is None
    failure = payout.failure
    assert failure is not None
    assert failure.code == DeclineCode.PAYOUT_FAILED
    assert failure.provider_code == "RETURNED"


def test_test_event_has_no_typed_object() -> None:
    event = _event("webhook.test", {"object": "webhook_endpoint", "id": "we_1"})
    assert event.payment is None
    assert event.refund is None
    assert event.recurring_payment is None
    assert event.payout is None
    assert event.object_type == "webhook_endpoint"


def test_missing_fields_fall_back() -> None:
    payment = PaymentObject.from_api({"object": "payment", "currency": "xx", "failure": {"code": ""}})

    assert payment.id == ""
    assert payment.currency == "PLN"
    assert payment.amount.minor == 0
    failure = payment.failure
    assert failure is not None
    assert failure.code == DeclineCode.GENERIC_DECLINE
    assert not failure.is_retryable
    assert failure.category is None


def test_strict_value_types() -> None:
    payment = PaymentObject.from_api(
        {
            "id": 42,
            "amount": "4999",
            "amount_refunded": 10.0,
            "amount_captured": True,
            "description": 1.5,
            "failure": {"code": 5, "retryable": 1, "provider_code": 51, "message": 7},
        }
    )
    assert payment.id == "42"
    assert payment.amount.minor == 0
    assert payment.amount_refunded.minor == 0
    assert payment.amount_captured.minor == 0
    assert payment.description is None
    failure = payment.failure
    assert failure is not None
    assert failure.code == DeclineCode.GENERIC_DECLINE
    assert not failure.is_retryable
    assert failure.provider_code == "51"
    assert failure.message is None
    assert PayoutObject.from_api({"failure": {"provider_code": False}}).failure is not None


def test_decline_catalog() -> None:
    assert len(DeclineCode.ALL) == 22
    assert len(set(DeclineCode.ALL)) == 22
    assert DeclineCode.ALL[0] == "insufficient_funds"
    assert DeclineCode.ALL[-1] == "processing_error"
    assert FailureCategory.ALL == ("customer", "merchant", "risk", "system")
