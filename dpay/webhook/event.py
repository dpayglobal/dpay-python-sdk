from __future__ import annotations

from typing import Any


def _string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


class WebhookEvent:
    """Webhook event envelope: ``{id, type, api_version, created, livemode, service, [merchant_ref], data}``.

    ``data.object`` stays a dict - payment, refund, recurring_payment or payout, amounts in minor units.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> WebhookEvent:
        return cls(data)

    @property
    def id(self) -> str:
        return _string(self.raw, "id") or ""

    @property
    def type(self) -> str:
        return _string(self.raw, "type") or ""

    @property
    def api_version(self) -> str | None:
        return _string(self.raw, "api_version")

    @property
    def created(self) -> str | None:
        """Event time in UTC (``YYYY-MM-DDTHH:MM:SSZ``) - not the delivery time, useless against replays."""
        return _string(self.raw, "created")

    @property
    def is_livemode(self) -> bool:
        return self.raw.get("livemode") is not False

    @property
    def service(self) -> str | None:
        """Service name, ``None`` for account events (payouts) and test events."""
        return _string(self.raw, "service")

    @property
    def merchant_ref(self) -> str | None:
        """Merchant reference, present only in events sent to a dpay Connect partner."""
        return _string(self.raw, "merchant_ref")

    @property
    def object(self) -> dict[str, Any]:
        data = self.raw.get("data")
        item = data.get("object") if isinstance(data, dict) else None
        return item if isinstance(item, dict) else {}

    @property
    def object_type(self) -> str | None:
        """``payment``, ``refund``, ``recurring_payment``, ``payout`` or ``webhook_endpoint``."""
        return _string(self.object, "object")


class EventPage:
    """One page of the Events API, newest events first.

    The API re-encodes the envelopes - do not verify webhook signatures on them.
    """

    def __init__(self, data: list[WebhookEvent], has_more: bool, next_starting_after: str | None) -> None:
        self.data = data
        self.has_more = has_more
        self.next_starting_after = next_starting_after

    @classmethod
    def from_api(cls, response: dict[str, Any]) -> EventPage:
        items = response.get("data")
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            items = []
        events = [WebhookEvent.from_api(item) for item in items if isinstance(item, dict)]
        next_starting_after = response.get("next_starting_after")
        return cls(
            events,
            response.get("has_more", False) is True,
            next_starting_after if isinstance(next_starting_after, str) else None,
        )
