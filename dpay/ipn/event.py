from __future__ import annotations

from typing import Any, Literal

from dpay._internal.php import is_numeric, is_scalar, php_int, php_strval
from dpay.exceptions import DPayValueError

IpnTypeValue = Literal["transfer", "capture", "dcb"]


class IpnType:
    TRANSFER = "transfer"
    # Deprecated: dpay no longer sends capture IPNs - use the ``payment.captured`` webhook event.
    CAPTURE = "capture"
    DCB = "dcb"

    ALL = (TRANSFER, CAPTURE, DCB)

    @staticmethod
    def assert_valid(value: str) -> None:
        if value not in IpnType.ALL:
            raise DPayValueError(f'Invalid IPN type "{value}"')


class IpnEvent:
    ACK = "OK"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    def _scalar(self, key: str, default: str | None) -> str | None:
        value = self.raw.get(key)
        return php_strval(value) if is_scalar(value) else default

    @property
    def id(self) -> str:
        return self._scalar("id", "") or ""

    @property
    def amount(self) -> str:
        return self._scalar("amount", "") or ""

    @property
    def email(self) -> str | None:
        return self._scalar("email", None)

    @property
    def type(self) -> str:
        return self._scalar("type", "") or ""

    @property
    def is_transfer(self) -> bool:
        return self.type == IpnType.TRANSFER

    @property
    def is_capture(self) -> bool:
        """Deprecated: dpay no longer sends capture IPNs - use the ``payment.captured`` webhook event."""
        return self.type == IpnType.CAPTURE

    @property
    def is_dcb(self) -> bool:
        return self.type == IpnType.DCB

    @property
    def attempt(self) -> int:
        value = self.raw.get("attempt")
        return php_int(value) if is_numeric(value) else 0

    @property
    def version(self) -> int:
        value = self.raw.get("version")
        return php_int(value) if is_numeric(value) else 0

    @property
    def custom(self) -> str | None:
        return self._scalar("custom", None)

    @property
    def capture_payment_id(self) -> str | None:
        """Deprecated: dpay no longer sends capture IPNs - use the ``payment.captured`` webhook event."""
        return self._scalar("capture_payment_id", None)

    @property
    def signature(self) -> str:
        return self._scalar("signature", "") or ""
