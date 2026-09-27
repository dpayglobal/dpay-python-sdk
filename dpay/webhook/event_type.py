from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from dpay.exceptions import DPayValueError

WebhookEventTypeValue = Literal[
    "payment.succeeded",
    "payment.failed",
    "payment.captured",
    "refund.succeeded",
    "refund.failed",
    "recurring_payment.activated",
    "recurring_payment.canceled",
    "recurring_payment.expired",
    "recurring_payment.declined",
    "payout.paid",
    "payout.failed",
    "webhook.test",
]


class WebhookEventType:
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_CAPTURED = "payment.captured"
    REFUND_SUCCEEDED = "refund.succeeded"
    REFUND_FAILED = "refund.failed"
    RECURRING_PAYMENT_ACTIVATED = "recurring_payment.activated"
    RECURRING_PAYMENT_CANCELED = "recurring_payment.canceled"
    RECURRING_PAYMENT_EXPIRED = "recurring_payment.expired"
    RECURRING_PAYMENT_DECLINED = "recurring_payment.declined"
    PAYOUT_PAID = "payout.paid"
    PAYOUT_FAILED = "payout.failed"
    WEBHOOK_TEST = "webhook.test"

    # Events a merchant endpoint can subscribe to and the Events API can filter on.
    MERCHANT = (
        PAYMENT_SUCCEEDED,
        PAYMENT_FAILED,
        PAYMENT_CAPTURED,
        REFUND_SUCCEEDED,
        REFUND_FAILED,
        RECURRING_PAYMENT_ACTIVATED,
        RECURRING_PAYMENT_CANCELED,
        RECURRING_PAYMENT_EXPIRED,
        RECURRING_PAYMENT_DECLINED,
        PAYOUT_PAID,
        PAYOUT_FAILED,
    )

    # Events allowed in the ``webhook`` object of a payment registration.
    PAYMENT_REGISTRATION = (
        PAYMENT_SUCCEEDED,
        PAYMENT_FAILED,
        PAYMENT_CAPTURED,
        REFUND_SUCCEEDED,
        REFUND_FAILED,
        RECURRING_PAYMENT_ACTIVATED,
        RECURRING_PAYMENT_CANCELED,
        RECURRING_PAYMENT_EXPIRED,
        RECURRING_PAYMENT_DECLINED,
    )

    # Events allowed in the ``webhook`` object of a refund.
    REFUND = (REFUND_SUCCEEDED, REFUND_FAILED)

    # Events allowed in the ``webhook`` object of a card capture.
    CAPTURE = (PAYMENT_CAPTURED,)

    def __init__(self) -> None:
        raise DPayValueError("WebhookEventType is not instantiable")

    @staticmethod
    def assert_allowed(events: Iterable[str], allowed: Iterable[str], context: str) -> None:
        permitted = tuple(allowed)
        for event in events:
            if event not in permitted:
                raise DPayValueError(f'Event "{event}" is not allowed in the webhook object of {context}')
