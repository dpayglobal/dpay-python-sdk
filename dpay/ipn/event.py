from __future__ import annotations

from typing import Any, Literal

from dpay._internal.php import is_numeric, is_scalar, php_int, php_strval
from dpay.exceptions import DPayValueError
from dpay.ipn.alias_update import AliasUpdate

IpnTypeValue = Literal["transfer", "capture", "dcb", "alias_update"]


class IpnType:
    TRANSFER = "transfer"
    # Deprecated: dpay no longer sends capture IPNs - use the ``payment.captured`` webhook event.
    CAPTURE = "capture"
    DCB = "dcb"
    # BLIK OneClick alias or recurring payment status change, sent to ``alias_ipn_url`` (or ``url_ipn``).
    ALIAS_UPDATE = "alias_update"

    ALL = (TRANSFER, CAPTURE, DCB, ALIAS_UPDATE)

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

    def _signed_transfer_field(self, key: str, default: str | None) -> str | None:
        # alias_update signs only id, type and version - a transfer field in its payload is ignored
        return default if self.is_alias_update else self._scalar(key, default)

    @property
    def id(self) -> str:
        """Payment ID - for alias_update the payment that registered the alias."""
        return self._scalar("id", "") or ""

    @property
    def amount(self) -> str:
        """Paid amount as sent (e.g. ``10.00``).

        Empty for alias_update - its signature does not cover an amount, so a value in the payload is ignored.
        """
        return self._signed_transfer_field("amount", "") or ""

    @property
    def email(self) -> str | None:
        """Payer's email; ``None`` for alias_update (not signed there)."""
        return self._signed_transfer_field("email", None)

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
    def is_alias_update(self) -> bool:
        """BLIK OneClick alias or recurring payment status change - details in ``alias_update``."""
        return self.type == IpnType.ALIAS_UPDATE

    @property
    def alias_update(self) -> AliasUpdate | None:
        """Alias change of an ``alias_update`` IPN; ``None`` for other types."""
        return AliasUpdate.from_api(self.raw) if self.is_alias_update else None

    @property
    def attempt(self) -> int:
        """Delivery attempt; 0 for alias_update (not signed there)."""
        if self.is_alias_update:
            return 0
        value = self.raw.get("attempt")
        return php_int(value) if is_numeric(value) else 0

    @property
    def version(self) -> int:
        value = self.raw.get("version")
        return php_int(value) if is_numeric(value) else 0

    @property
    def custom(self) -> str | None:
        """The ``custom`` value of the registration; ``None`` for alias_update (not signed there)."""
        return self._signed_transfer_field("custom", None)

    @property
    def capture_payment_id(self) -> str | None:
        """Deprecated: dpay no longer sends capture IPNs - use the ``payment.captured`` webhook event."""
        return self._scalar("capture_payment_id", None)

    @property
    def signature(self) -> str:
        return self._scalar("signature", "") or ""
