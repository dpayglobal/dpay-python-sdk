from __future__ import annotations

from typing import Any

from dpay._internal.php import is_php_int


class DeclineCode:
    """dpay decline codes (``failure.code`` of webhook objects).

    React to a decline by ``Failure.category`` and ``Failure.is_retryable``; new codes may appear - treat
    an unknown code like ``generic_decline``.
    """

    INSUFFICIENT_FUNDS = "insufficient_funds"
    LIMIT_EXCEEDED = "limit_exceeded"
    CUSTOMER_DECLINED = "customer_declined"
    CUSTOMER_TIMEOUT = "customer_timeout"
    INVALID_CODE = "invalid_code"
    EXPIRED = "expired"
    APP_UPDATE_REQUIRED = "app_update_required"
    ISSUER_DECLINED = "issuer_declined"
    CARD_INVALID = "card_invalid"
    AUTHENTICATION_REQUIRED = "authentication_required"
    ALIAS_INVALID = "alias_invalid"
    UNSUPPORTED_BY_BANK = "unsupported_by_bank"
    GENERIC_DECLINE = "generic_decline"
    SECURITY_DECLINED = "security_declined"
    BLOCKED = "blocked"
    RECURRING_CONDITIONS_NOT_MET = "recurring_conditions_not_met"
    INVALID_REQUEST = "invalid_request"
    REFUND_WINDOW_EXPIRED = "refund_window_expired"
    REFUND_AMOUNT_EXCEEDED = "refund_amount_exceeded"
    PAYOUT_FAILED = "payout_failed"
    REFUND_FAILED = "refund_failed"
    PROCESSING_ERROR = "processing_error"

    ALL = (
        INSUFFICIENT_FUNDS,
        LIMIT_EXCEEDED,
        CUSTOMER_DECLINED,
        CUSTOMER_TIMEOUT,
        INVALID_CODE,
        EXPIRED,
        APP_UPDATE_REQUIRED,
        ISSUER_DECLINED,
        CARD_INVALID,
        AUTHENTICATION_REQUIRED,
        ALIAS_INVALID,
        UNSUPPORTED_BY_BANK,
        GENERIC_DECLINE,
        SECURITY_DECLINED,
        BLOCKED,
        RECURRING_CONDITIONS_NOT_MET,
        INVALID_REQUEST,
        REFUND_WINDOW_EXPIRED,
        REFUND_AMOUNT_EXCEEDED,
        PAYOUT_FAILED,
        REFUND_FAILED,
        PROCESSING_ERROR,
    )


class FailureCategory:
    """Who can fix a decline (``failure.category``)."""

    # The customer (funds, limits, code, bank app) - they can pay again.
    CUSTOMER = "customer"
    # Your request or configuration.
    MERCHANT = "merchant"
    # Security checks - do not retry automatically.
    RISK = "risk"
    # dpay or the provider - temporary errors.
    SYSTEM = "system"

    ALL = (CUSTOMER, MERCHANT, RISK, SYSTEM)


class Failure:
    """Decline reason of a webhook object (``failure``): payment.failed, refund.failed, payout.failed."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Failure:
        return cls(data)

    @property
    def code(self) -> str:
        """dpay decline code (``DeclineCode``), e.g. ``insufficient_funds``."""
        code = self.raw.get("code")
        return code if isinstance(code, str) and code != "" else DeclineCode.GENERIC_DECLINE

    @property
    def message(self) -> str | None:
        """English description of the code."""
        message = self.raw.get("message")
        return message if isinstance(message, str) else None

    @property
    def category(self) -> str | None:
        """customer, merchant, risk or system (``FailureCategory``)."""
        category = self.raw.get("category")
        return category if isinstance(category, str) else None

    @property
    def is_retryable(self) -> bool:
        """Whether the same payment may succeed when tried again (e.g. after topping up the account)."""
        return self.raw.get("retryable", False) is True

    @property
    def provider_code(self) -> str | None:
        """Original provider code (e.g. a BLIK code), or for payout_failed what happened to the funds."""
        value = self.raw.get("provider_code")
        if isinstance(value, str):
            return value
        return str(value) if is_php_int(value) else None
