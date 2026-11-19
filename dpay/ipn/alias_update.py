from __future__ import annotations

from typing import Any

from dpay._internal.php import is_php_int


class AliasUpdate:
    """Payload of an ``alias_update`` IPN.

    A BLIK OneClick alias (alias type UID) or a recurring payment (PAYID) changed its status. Sent to
    ``alias_ipn_url`` from the registration, or to ``url_ipn`` without it.

    The signature covers only ``id``, ``type`` and ``version`` - none of the fields below. Anyone who has seen
    one alias_update of a payment can replay it with a different status, so before acting on a change (e.g.
    stopping a subscription) confirm the current state with ``client.recurring.status()`` or
    ``client.blik.alias()``.
    """

    CHANGE_REGISTER = "ALIAS_REGISTER"
    CHANGE_UPDATE = "ALIAS_UPDATE"
    CHANGE_UNREGISTER = "ALIAS_UNREGISTER"
    CHANGE_EXPIRED = "ALIAS_EXPIRED"
    CHANGE_DECLINED = "ALIAS_DECLINED"

    ALIAS_TYPE_UID = "UID"
    ALIAS_TYPE_PAYID = "PAYID"

    STATUS_ACTIVE = "ACTIVE"
    STATUS_INACTIVE = "INACTIVE"
    STATUS_UNREGISTERED = "UNREGISTERED"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_DECLINED = "DECLINED"

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AliasUpdate:
        return cls(data)

    def _string(self, key: str) -> str | None:
        value = self.raw.get(key)
        if isinstance(value, str):
            return value
        return str(value) if is_php_int(value) else None

    @property
    def change_type(self) -> str | None:
        """ALIAS_REGISTER, ALIAS_UPDATE, ALIAS_UNREGISTER, ALIAS_EXPIRED or ALIAS_DECLINED."""
        return self._string("change_type")

    @property
    def alias_type(self) -> str | None:
        """UID (BLIK OneClick) or PAYID (recurring payment)."""
        return self._string("alias_type")

    @property
    def alias_status(self) -> str | None:
        """ACTIVE, INACTIVE, UNREGISTERED, EXPIRED or DECLINED."""
        return self._string("alias_status")

    @property
    def is_active(self) -> bool:
        return self.alias_status == AliasUpdate.STATUS_ACTIVE

    @property
    def alias_key(self) -> str | None:
        """Alias identifier at BLIK - not the alias value you send with payments."""
        return self._string("alias_key")

    @property
    def alias_label(self) -> str | None:
        return self._string("alias_label")

    @property
    def alias_expire_at(self) -> str | None:
        return self._string("alias_expire_at")

    @property
    def change_reason_category(self) -> str | None:
        return self._string("change_reason_category")

    @property
    def change_reason_message(self) -> str | None:
        return self._string("change_reason_message")
