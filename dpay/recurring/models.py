from __future__ import annotations

import re
from typing import Any

from dpay._internal.php import is_php_bool, is_php_int, is_scalar, php_strval

_DIGITS = re.compile(r"[0-9]+")


def _string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _minor_units(raw: dict[str, Any], key: str) -> int | None:
    # An int, or a string of digits only (PHP ctype_digit)
    value = raw.get(key)
    if isinstance(value, int) and is_php_int(value):
        return value
    if isinstance(value, str) and _DIGITS.fullmatch(value) is not None:
        return int(value)
    return None


class RecurringRegistrationInfo:
    """Terms of a registered recurring payment, as returned by the status endpoint (amounts in grosz)."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecurringRegistrationInfo:
        return cls(data)

    @property
    def transaction_id(self) -> str | None:
        """transactionId of the registering payment."""
        return _string(self.raw, "transaction_id")

    @property
    def label(self) -> str | None:
        return _string(self.raw, "label")

    @property
    def model(self) -> str | None:
        return _string(self.raw, "model")

    @property
    def frequency(self) -> str | None:
        return _string(self.raw, "frequency")

    @property
    def limit_amt(self) -> int | None:
        return _minor_units(self.raw, "limit_amt")

    @property
    def tot_limit_amt(self) -> int | None:
        return _minor_units(self.raw, "tot_limit_amt")

    @property
    def is_limit_amt_fixed(self) -> bool | None:
        value = self.raw.get("is_limit_amt_fixed")
        return value if is_php_bool(value) else None

    @property
    def init_date(self) -> str | None:
        return _string(self.raw, "init_date")

    @property
    def terms_url(self) -> str | None:
        return _string(self.raw, "terms_url")

    @property
    def terms_version(self) -> str | None:
        return _string(self.raw, "terms_version")

    @property
    def registered_at(self) -> str | None:
        """ISO 8601 with offset."""
        return _string(self.raw, "registered_at")


class RecurringStatus:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNREGISTERED = "UNREGISTERED"
    EXPIRED = "EXPIRED"
    DECLINED = "DECLINED"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.alias = _string(raw, "alias") or ""
        # Payment method of the recurring payment, e.g. ``blik``.
        self.method = _string(raw, "method")
        # ACTIVE, INACTIVE (waiting for the customer), UNREGISTERED, EXPIRED, DECLINED or None.
        self.status = _string(raw, "status")
        self.expiration_date = _string(raw, "expiration_date")
        registration = raw.get("registration")
        self.registration = (
            RecurringRegistrationInfo.from_api(registration) if isinstance(registration, dict) else None
        )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecurringStatus:
        return cls(data)

    @property
    def is_active(self) -> bool:
        return self.status == RecurringStatus.ACTIVE


class RecurringRetryResult:
    """Result of retrying a declined recurring charge.

    ``pending`` - the retry went to the bank, the outcome comes like for a charge (webhook, IPN, status);
    ``failed`` - the bank declined it at once (code in ``error_code``).
    """

    STATUS_PENDING = "pending"
    STATUS_FAILED = "failed"
    STATUS_SUCCESS = "success"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        retry = raw.get("retry")
        retry = retry if isinstance(retry, dict) else {}
        transaction_id = raw.get("transactionId")
        self.transaction_id = php_strval(transaction_id) if is_scalar(transaction_id) else ""
        self.status = _string(retry, "status")
        count = retry.get("count")
        # Which retry this was (1-3).
        self.count: int | None = count if is_php_int(count) else None
        self.error_code = _string(retry, "error")
        self.error_description = _string(retry, "error_description")

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecurringRetryResult:
        return cls(data)

    @property
    def is_pending(self) -> bool:
        return self.status == RecurringRetryResult.STATUS_PENDING

    @property
    def is_failed(self) -> bool:
        return self.status == RecurringRetryResult.STATUS_FAILED
